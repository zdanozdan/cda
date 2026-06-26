"""Streamlit UI for CdA calculator."""

from __future__ import annotations

import hashlib
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cda_calc.garmin_splits import (
    align_laps_to_ride,
    lap_label,
    parse_garmin_splits_csv,
    selected_lap_ranges,
)
from cda_calc.i18n import CDA_REFERENCE_ROW_KEYS, fmt_decimal, language_selector, t
from cda_calc.models import AnalysisParams
from cda_calc.optimizer import compute_ve_with_cda, optimize_cda
from cda_calc.physics import (
    air_density_kg_m3,
    compute_dt_seconds,
    normalized_power,
    rmse_ve,
    steady_flat_power_w,
    steady_flat_speed_kph,
    virtual_elevation,
)
from cda_calc.presets import DEFAULT_PRESET_INDEX, GP5000_TT_PRESETS, preset_by_index, preset_labels
from cda_calc.segment import (
    clamp_segment_km,
    extract_km_range_from_plotly_selection,
    km_range_to_indices,
    riding_duration_seconds,
    slice_ride_km_ranges,
    total_distance_km,
)
from cda_calc.tcx_parser import parse_tcx, slice_ride

if "lang" not in st.session_state:
    st.session_state.lang = "pl"

st.set_page_config(page_title=t("page_title"), page_icon="🚴", layout="wide")

title_col, lang_col = st.columns([6, 1])
with title_col:
    st.title(t("title"))
with lang_col:
    language_selector()

st.markdown(t("seo_intro"))

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        display: none;
    }
    div[data-testid="stMainBlockContainer"] {
        padding-top: 1rem;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }
    h1 {
        margin-top: 0;
        padding-top: 0;
    }
    div[data-testid="stDialog"] [data-baseweb="modal"] > div:first-child {
        background: rgba(15, 23, 42, 0.55) !important;
    }
    div[data-testid="stDialog"] div[role="dialog"] {
        width: 80vw !important;
        max-width: 80vw !important;
        background: #f8fafc !important;
        border: 2px solid #2563eb !important;
        border-radius: 12px !important;
        box-shadow: 0 24px 64px rgba(15, 23, 42, 0.35) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

INDIRECT_CDA_PDF_URL = "https://raceyourtrack.com/static/docs/indirect-cda.pdf"

CDA_REFERENCE_MASS_KG = 70.0


def _cda_reference_power_range(cda_lo: float, cda_hi: float, crr: float) -> str:
    p_lo = steady_flat_power_w(cda_lo, CDA_REFERENCE_MASS_KG, crr=crr)
    p_hi = steady_flat_power_w(cda_hi, CDA_REFERENCE_MASS_KG, crr=crr)
    return f"{round(p_lo)}–{round(p_hi)}"


def _cda_reference_table_markdown() -> str:
    lines = [
        f"| {t('ref_table_who')} | {t('ref_table_cda')} | {t('ref_table_power')} |",
        "|---------------|----------|----------------------|",
    ]
    for key, cda_lo, cda_hi, crr in CDA_REFERENCE_ROW_KEYS:
        cda_range = f"{fmt_decimal(cda_lo)}–{fmt_decimal(cda_hi)}"
        power_range = _cda_reference_power_range(cda_lo, cda_hi, crr)
        lines.append(f"| {t(key)} | {cda_range} | {power_range} |")
    return "\n".join(lines)


protocol_col, reference_col = st.columns([3, 2], gap="large")
with protocol_col:
    st.markdown(t("protocol", pdf_url=INDIRECT_CDA_PDF_URL))
with reference_col:
    st.markdown(t("ref_scale_title"))
    st.markdown(_cda_reference_table_markdown())
    st.caption(t("ref_scale_caption", mass=CDA_REFERENCE_MASS_KG))

SEGMENT_CHART_KEY = "segment_plot"
SEGMENT_KM_SLIDER_KEY = "segment_km_slider"


def _cda_help_markdown() -> str:
    return t(
        "help_body",
        ref_table=_cda_reference_table_markdown(),
        mass=CDA_REFERENCE_MASS_KG,
    )


def _cda_help_dialog() -> None:
    st.markdown(_cda_help_markdown())


def _format_duration_hms(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_duration_minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f} min"


def _format_signed_watts(delta: float) -> str:
    if abs(delta) < 0.5:
        return "≈0 W"
    sign = "+" if delta > 0 else "−"
    return f"{sign}{abs(round(delta))} W"


def _format_signed_speed_kph(delta: float) -> str:
    if abs(delta) < 0.05:
        return "≈0 km/h"
    sign = "+" if delta > 0 else "−"
    return f"{sign}{abs(delta):.1f} km/h"


def _format_signed_duration(seconds: float) -> str:
    if abs(seconds) < 0.5:
        return "≈0 s"
    sign = "+" if seconds > 0 else "−"
    return f"{sign}{_format_duration_hms(abs(seconds))}"


def _flat_time_seconds(distance_km: float, speed_kph: float) -> float:
    if speed_kph <= 0 or distance_km <= 0:
        return float("inf")
    return distance_km / speed_kph * 3600.0


def _cda_manual_comparison_table(
    cda_computed: float,
    cda_manual: float,
    *,
    mass_kg: float,
    crr: float,
    rho: float,
    drivetrain_loss: float,
    ref_power_w: float,
    distance_km: float,
) -> str:
    flat_kw = {
        "mass_kg": mass_kg,
        "crr": crr,
        "air_density": rho,
        "drivetrain_loss_pct": drivetrain_loss,
    }
    speed_kw = {k: v for k, v in flat_kw.items() if k != "mass_kg"}
    p_computed_40 = steady_flat_power_w(cda_computed, **flat_kw)
    p_manual_40 = steady_flat_power_w(cda_manual, **flat_kw)
    speed_computed = steady_flat_speed_kph(cda_computed, mass_kg, ref_power_w, **speed_kw)
    speed_manual = steady_flat_speed_kph(cda_manual, mass_kg, ref_power_w, **speed_kw)
    time_computed = _flat_time_seconds(distance_km, speed_computed)
    time_manual = _flat_time_seconds(distance_km, speed_manual)

    ref_power = round(ref_power_w)
    dist_label = f"{distance_km:.2f} km"
    return f"""
| {t('table_metric')} | {t('table_computed', cda=cda_computed)} | {t('table_slider', cda=cda_manual)} | {t('table_diff')} |
|---------|--------------------------------------|--------------------------------|--------|
| {t('table_power_40')} | {round(p_computed_40)} W | {round(p_manual_40)} W | {_format_signed_watts(p_manual_40 - p_computed_40)} |
| {t('table_speed_at_power', power=ref_power)} | {speed_computed:.1f} km/h | {speed_manual:.1f} km/h | {_format_signed_speed_kph(speed_manual - speed_computed)} |
| {t('table_time_at_distance', distance=dist_label)} | {_format_duration_hms(time_computed)} | {_format_duration_hms(time_manual)} | {_format_signed_duration(time_manual - time_computed)} |
"""


def _plot_power_speed(
    df_full: pd.DataFrame,
    highlight_ranges: list[tuple[float, float]],
    boundary_km: list[float] | None = None,
) -> go.Figure:
    x_km = df_full["distance_m"] / 1000
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_km,
            y=df_full["power_w"],
            name=t("chart_power"),
            line=dict(color="#f59e0b", width=1.5),
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_km,
            y=df_full["speed_mps"] * 3.6,
            name=t("chart_speed"),
            line=dict(color="#2563eb", width=1.5),
            yaxis="y2",
        )
    )
    for km_start, km_end in highlight_ranges:
        fig.add_vrect(
            x0=km_start,
            x1=km_end,
            fillcolor="rgba(37, 99, 235, 0.12)",
            layer="below",
            line_width=0,
        )
    if boundary_km:
        for km in boundary_km:
            fig.add_vline(x=km, line_color="rgba(100, 116, 139, 0.35)", line_width=1)
    fig.update_layout(
        title=t("chart_power_speed"),
        xaxis_title=t("chart_distance"),
        yaxis=dict(title=t("chart_power"), color="#f59e0b"),
        yaxis2=dict(
            title=t("chart_speed"),
            overlaying="y",
            side="right",
            color="#2563eb",
        ),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=50, r=50, t=60, b=40),
        dragmode="select",
    )
    return fig


def _update_segment_from_chart(ride_total_km: float, event) -> bool:
    km_range = extract_km_range_from_plotly_selection(event)
    if km_range is None:
        return False
    clamped = clamp_segment_km(*km_range, ride_total_km)
    if clamped == tuple(st.session_state.get("segment_km", clamped)):
        return False
    st.session_state.segment_km = clamped
    st.session_state.pop(SEGMENT_KM_SLIDER_KEY, None)
    st.session_state.pop("computed_for_segment", None)
    st.session_state.analysis_result = None
    return True


def _plot_ve(df: pd.DataFrame, ve: pd.Series, valid_mask: pd.Series, title: str) -> go.Figure:
    fig = go.Figure()
    invalid = ~valid_mask
    if invalid.any():
        fig.add_trace(
            go.Scatter(
                x=df.loc[invalid, "distance_m"] / 1000,
                y=df.loc[invalid, "elevation_m"],
                mode="markers",
                name=t("chart_elev_rejected"),
                marker=dict(color="lightgray", size=4),
            )
        )
    fig.add_trace(
        go.Scatter(
            x=df.loc[valid_mask, "distance_m"] / 1000,
            y=df.loc[valid_mask, "elevation_m"],
            mode="lines",
            name=t("chart_elev_measured"),
            line=dict(color="#2563eb", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["distance_m"] / 1000,
            y=ve,
            mode="lines",
            name=t("chart_virtual_elevation"),
            line=dict(color="#dc2626", width=2, dash="dash"),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=t("chart_distance"),
        yaxis_title=t("chart_height"),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def _plot_residuals(df: pd.DataFrame, residuals: pd.Series, valid_mask: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.loc[valid_mask, "distance_m"] / 1000,
            y=residuals.loc[valid_mask],
            mode="lines",
            name=t("chart_residuals_valid"),
            line=dict(color="#7c3aed"),
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=t("chart_residuals"),
        xaxis_title=t("chart_distance"),
        yaxis_title="Δh (m)",
        height=280,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


with st.sidebar:
    st.header(t("sidebar_settings"))
    mass_kg = st.number_input(t("mass_kg"), min_value=50.0, max_value=150.0, value=74.0, step=0.5)

    preset_idx = st.selectbox(
        t("tires_preset"),
        range(len(GP5000_TT_PRESETS)),
        format_func=lambda i: preset_labels()[i],
        index=DEFAULT_PRESET_INDEX,
    )
    preset = preset_by_index(preset_idx)
    if preset.estimated:
        st.caption(t("crr_estimated"))

    crr = st.slider(
        t("crr_slider"),
        min_value=0.0015,
        max_value=0.0050,
        value=float(preset.crr),
        step=0.0001,
        format="%.4f",
    )

    st.subheader(t("air_section"))
    temp_c = st.number_input(t("temperature"), value=20.0, step=1.0)
    altitude_m = st.number_input(t("altitude"), value=100.0, step=10.0)
    humidity = st.slider(t("humidity"), 0, 100, 50)
    rho = air_density_kg_m3(temp_c, altitude_m, humidity)
    st.metric(t("air_density"), f"{rho:.4f} kg/m³")

    drivetrain_loss = st.slider(t("drivetrain_loss"), 0.0, 5.0, 2.0, 0.5)

    st.subheader(t("filters_section"))
    min_speed_kph = st.slider(t("min_speed"), 0, 60, 29, 1)
    max_speed_kph = st.slider(
        t("max_speed"),
        0,
        100,
        0,
        1,
        help=t("max_speed_help"),
    )
    min_power = st.slider(t("min_power"), 0, 400, 150, 10)
    filter_accel = st.checkbox(t("filter_accel"), value=True)
    min_coverage = st.slider(t("min_coverage"), 10, 100, 30)

uploaded = st.file_uploader(t("upload_tcx"), type=["tcx"])

if uploaded is None:
    st.info(t("upload_info"))
    st.stop()

tcx_bytes = uploaded.getvalue()

try:
    file_hash = hashlib.sha256(tcx_bytes).hexdigest()
    if st.session_state.get("file_hash") != file_hash:
        st.session_state.file_hash = file_hash
        st.session_state.pop("analysis_result", None)
        st.session_state.pop("cda_slider", None)
        st.session_state.pop("segment_km", None)
        st.session_state.pop(SEGMENT_CHART_KEY, None)
        st.session_state.pop(SEGMENT_KM_SLIDER_KEY, None)
        st.session_state.pop("computed_for_segment", None)
        st.session_state.pop("splits_hash", None)
        st.session_state.pop("selected_lap_numbers", None)
    ride = parse_tcx(io.BytesIO(tcx_bytes))
except ValueError as e:
    st.error(str(e))
    st.stop()

df_full = ride.df
ride_total_km = total_distance_km(df_full)

if ride_total_km <= 0:
    st.error(t("distance_error"))
    st.stop()

if ride.speed_source == "gps":
    st.warning(t("speed_gps_warning"))
elif ride.speed_source == "mixed":
    st.warning(t("speed_mixed_warning"))

splits_upload = st.file_uploader(
    t("upload_splits"),
    type=["csv"],
    help=t("upload_splits_help"),
)

splits_bytes: bytes | None = splits_upload.getvalue() if splits_upload is not None else None

garmin_laps = []
if splits_bytes is not None:
    try:
        splits_hash = hashlib.sha256(splits_bytes).hexdigest()
        if st.session_state.get("splits_hash") != splits_hash:
            st.session_state.splits_hash = splits_hash
            st.session_state.selected_lap_numbers = None
            st.session_state.pop("lap_multiselect", None)
            st.session_state.pop("computed_for_segment", None)
            st.session_state.analysis_result = None
        garmin_laps = align_laps_to_ride(
            parse_garmin_splits_csv(io.BytesIO(splits_bytes)),
            ride_total_km,
        )
    except ValueError as exc:
        st.error(t("splits_error", error=exc))
        garmin_laps = []

use_lap_mode = False
selected_lap_numbers: list[int] = []
lap_boundaries_km: list[float] = []

if garmin_laps:
    csv_total_km = garmin_laps[-1].km_end
    if abs(csv_total_km - ride_total_km) / max(csv_total_km, 1.0) > 0.05:
        st.warning(t("csv_distance_warning", csv=csv_total_km, tcx=ride_total_km))

    stored_mode = st.session_state.get("segment_mode")
    if stored_mode not in ("laps", "manual", None):
        st.session_state.segment_mode = (
            "laps" if stored_mode and ("CSV" in str(stored_mode) or "Laps" in str(stored_mode)) else "manual"
        )

    segment_mode = st.radio(
        t("segment_mode_label"),
        options=["laps", "manual"],
        format_func=lambda mode: t("segment_mode_laps") if mode == "laps" else t("segment_mode_manual"),
        horizontal=True,
        key="segment_mode",
    )
    use_lap_mode = segment_mode == "laps"
    lap_boundaries_km = [lap.km_end for lap in garmin_laps[:-1]]

    if use_lap_mode:
        all_lap_numbers = [lap.number for lap in garmin_laps]
        if "lap_multiselect" not in st.session_state:
            st.session_state.lap_multiselect = all_lap_numbers

        selected_lap_numbers = st.multiselect(
            t("laps_multiselect"),
            options=all_lap_numbers,
            format_func=lambda n: lap_label(
                next(lap for lap in garmin_laps if lap.number == n),
                lap_word=t("lap_word"),
            ),
            key="lap_multiselect",
        )
        st.session_state.selected_lap_numbers = selected_lap_numbers
        if not selected_lap_numbers:
            st.warning(t("select_lap_warning"))

if "segment_km" not in st.session_state:
    st.session_state.segment_km = (0.0, ride_total_km)
else:
    clamped = clamp_segment_km(*st.session_state.segment_km, ride_total_km)
    if clamped != tuple(st.session_state.segment_km):
        st.session_state.segment_km = clamped
        st.session_state.pop(SEGMENT_KM_SLIDER_KEY, None)

if use_lap_mode and selected_lap_numbers:
    chart_highlight_ranges = selected_lap_ranges(garmin_laps, selected_lap_numbers)
else:
    chart_km_start, chart_km_end = clamp_segment_km(*st.session_state.segment_km, ride_total_km)
    chart_highlight_ranges = [(chart_km_start, chart_km_end)]

chart_event = st.plotly_chart(
    _plot_power_speed(
        df_full,
        chart_highlight_ranges,
        boundary_km=lap_boundaries_km if garmin_laps else None,
    ),
    use_container_width=True,
    on_select="rerun",
    selection_mode=["box", "points"],
    key=SEGMENT_CHART_KEY,
)
if use_lap_mode:
    st.caption(t("chart_caption_laps"))
else:
    st.caption(t("chart_caption_manual"))
if not use_lap_mode and _update_segment_from_chart(ride_total_km, chart_event):
    st.rerun()

if not use_lap_mode:
    seg_col1, seg_col2 = st.columns([4, 1])
    with seg_col1:
        km_start, km_end = st.slider(
            t("segment_slider"),
            min_value=0.0,
            max_value=float(ride_total_km),
            value=clamp_segment_km(*st.session_state.segment_km, ride_total_km),
            step=0.05,
            format="%.2f",
            key=SEGMENT_KM_SLIDER_KEY,
            help=t("segment_slider_help"),
        )
    with seg_col2:
        st.write("")
        if st.button(t("whole_ride_btn"), use_container_width=True):
            st.session_state.segment_km = (0.0, ride_total_km)
            st.session_state.pop(SEGMENT_KM_SLIDER_KEY, None)
            st.session_state.pop("computed_for_segment", None)
            st.session_state.analysis_result = None
            st.rerun()
    st.session_state.segment_km = (float(km_start), float(km_end))

if use_lap_mode and selected_lap_numbers:
    df = slice_ride_km_ranges(df_full, selected_lap_ranges(garmin_laps, selected_lap_numbers))
    current_segment = ("laps", tuple(sorted(selected_lap_numbers)))
elif use_lap_mode:
    st.warning(t("select_lap_continue"))
    st.stop()
else:
    km_start, km_end = st.session_state.segment_km
    range_start, range_end = km_range_to_indices(df_full, km_start, km_end)
    df = slice_ride(df_full, range_start, range_end)
    current_segment = ("km", st.session_state.segment_km)

duration_s = riding_duration_seconds(df)
seg_dist_km = (df["distance_m"].iloc[-1] - df["distance_m"].iloc[0]) / 1000
if use_lap_mode:
    selected_laps = [lap for lap in garmin_laps if lap.number in selected_lap_numbers]
    seg_dist_km = sum(lap.distance_km for lap in selected_laps)

avg_power = df["power_w"].mean()
np_w = normalized_power(df["power_w"].to_numpy(), compute_dt_seconds(df["timestamp"]))
avg_speed_kph = df["speed_mps"].mean() * 3.6

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric(t("segment_time"), _format_duration_minutes(duration_s))
    st.caption(_format_duration_hms(duration_s))
m2.metric(t("segment_distance"), f"{seg_dist_km:.2f} km")
m3.metric(t("avg_power"), f"{avg_power:.0f} W")
m4.metric(t("normalized_power"), f"{np_w:.0f} W" if np.isfinite(np_w) else "—")
m5.metric(t("avg_speed"), f"{avg_speed_kph:.1f} km/h")

params = AnalysisParams(
    mass_kg=mass_kg,
    crr=crr,
    air_density=rho,
    drivetrain_loss_pct=drivetrain_loss,
    min_speed_mps=min_speed_kph / 3.6,
    max_speed_mps=max_speed_kph / 3.6 if max_speed_kph > 0 else None,
    min_power_w=min_power,
    max_accel_mps2=0.5 if filter_accel else None,
    min_coverage_pct=min_coverage,
)

if "cda_slider" not in st.session_state:
    st.session_state.cda_slider = 0.22
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

btn_col1, btn_col2 = st.columns([1, 3])
with btn_col1:
    compute_clicked = st.button(t("compute_cda"), type="primary", use_container_width=True, key="compute_cda_btn")
with btn_col2:
    if st.session_state.get("compute_error"):
        st.error(st.session_state.compute_error)

if compute_clicked:
    st.session_state.pop("compute_success", None)
    st.session_state.pop("compute_error", None)
    try:
        with st.spinner(t("optimizing")):
            opt_result = optimize_cda(df, params)
        st.session_state.analysis_result = opt_result
        st.session_state.cda_slider = round(opt_result.cda_optimal, 3)
        st.session_state.computed_for_segment = current_segment
        st.session_state.compute_success = t(
            "compute_success",
            cda=opt_result.cda_optimal,
            rmse=opt_result.rmse,
            coverage=opt_result.coverage_pct,
        )
        st.rerun()
    except Exception as exc:
        st.session_state.compute_error = t("compute_error", error=exc)
        st.session_state.analysis_result = None
        st.rerun()

if st.session_state.get("compute_success"):
    st.success(st.session_state.compute_success)

result = st.session_state.get("analysis_result")
if result and st.session_state.get("computed_for_segment") != current_segment:
    st.warning(t("segment_changed"))
    result = None

cda_slider_col, cda_help_col = st.columns([11, 1], vertical_alignment="top")
with cda_help_col:
    if st.button(
        "",
        key="cda_help_btn",
        icon=":material/help:",
        type="tertiary",
        help=t("help_dialog_tooltip"),
    ):
        st.dialog(t("help_dialog_title"), width="large")(_cda_help_dialog)()
with cda_slider_col:
    cda_manual = st.slider(
        t("cda_slider"),
        min_value=0.15,
        max_value=0.35,
        step=0.001,
        format="%.3f",
        key="cda_slider",
    )

params_display = AnalysisParams(**{**params.__dict__, "cda": cda_manual})
ve, residuals, valid_mask = compute_ve_with_cda(df, params_display)
current_rmse = rmse_ve(virtual_elevation(df, params_display), df["elevation_m"], valid_mask)
stats = result.filter_stats if result else None
if stats is None:
    from cda_calc.filters import apply_quality_mask
    from cda_calc.physics import compute_acceleration, compute_dt_seconds, smooth_speed

    dt = compute_dt_seconds(df["timestamp"])
    speed_s = smooth_speed(df["speed_mps"].to_numpy(), dt)
    accel = compute_acceleration(speed_s, dt)
    _, stats = apply_quality_mask(
        df,
        min_speed_mps=min_speed_kph / 3.6,
        max_speed_mps=max_speed_kph / 3.6 if max_speed_kph > 0 else None,
        min_power_w=min_power,
        max_accel_mps2=0.5 if filter_accel else None,
        accel=accel,
    )

c1, c2, c3, c4 = st.columns(4)
c1.metric(t("cda_slider_metric"), f"{cda_manual:.3f} m²")
if result:
    c2.metric(t("cda_computed_metric"), f"{result.cda_optimal:.3f} m²")
    c3.metric(t("rmse_ve"), f"{current_rmse:.2f} m")
    c4.metric(t("data_coverage"), f"{stats.pct_valid:.1f}% ({stats.n_valid}/{stats.n_total})")
else:
    c2.metric(t("cda_computed_metric"), "—")
    c3.metric(t("rmse_ve"), f"{current_rmse:.2f} m")
    c4.metric(t("data_coverage"), f"{stats.pct_valid:.1f}% ({stats.n_valid}/{stats.n_total})")

if result is None:
    if use_lap_mode:
        st.info(t("info_laps"))
    else:
        st.info(t("info_manual"))

if stats.pct_valid < min_coverage:
    st.warning(t("low_coverage", pct=stats.pct_valid, min_pct=min_coverage))

if result and abs(cda_manual - result.cda_optimal) > 0.001:
    st.markdown(t("comparison_title"))
    st.markdown(
        _cda_manual_comparison_table(
            result.cda_optimal,
            cda_manual,
            mass_kg=mass_kg,
            crr=crr,
            rho=rho,
            drivetrain_loss=drivetrain_loss,
            ref_power_w=avg_power,
            distance_km=seg_dist_km,
        )
    )
    st.caption(
        t(
            "comparison_caption",
            mass=mass_kg,
            crr=crr,
            rho=rho,
            loss=drivetrain_loss,
            power=avg_power,
        )
    )

st.plotly_chart(
    _plot_ve(df, ve, valid_mask, t("chart_ve_title")),
    use_container_width=True,
)
st.plotly_chart(_plot_residuals(df, residuals, valid_mask), use_container_width=True)

with st.expander(t("filter_details")):
    st.write(
        f"- {t('filter_low_speed')}: **{stats.rejected_low_speed}**\n"
        f"- {t('filter_high_speed')}: **{stats.rejected_high_speed}**\n"
        f"- {t('filter_low_power')}: **{stats.rejected_low_power}**\n"
        f"- {t('filter_high_accel')}: **{stats.rejected_high_accel}**"
    )

with st.expander(t("limitations")):
    st.markdown(t("limitations_body"))
