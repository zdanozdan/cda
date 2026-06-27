"""GPS route map for Streamlit / Plotly."""

from __future__ import annotations

import math
from typing import Callable

import pandas as pd
import plotly.graph_objects as go

from cda_calc.tcx_parser import _haversine_m


def _valid_gps(lat, lon) -> bool:
    if lat is None or lon is None:
        return False
    try:
        return bool(pd.notna(lat) and pd.notna(lon))
    except TypeError:
        return False


def gps_runs(df: pd.DataFrame, max_gap_m: float = 400.0) -> list[pd.DataFrame]:
    """Split ride into contiguous GPS polylines (missing coords or large jumps break a run)."""
    runs: list[pd.DataFrame] = []
    rows: list[dict] = []
    prev_lat: float | None = None
    prev_lon: float | None = None

    def flush() -> None:
        nonlocal rows, prev_lat, prev_lon
        if rows:
            runs.append(pd.DataFrame(rows))
        rows = []
        prev_lat = prev_lon = None

    for _, row in df.iterrows():
        lat, lon = row.get("latitude"), row.get("longitude")
        if not _valid_gps(lat, lon):
            flush()
            continue

        lat_f, lon_f = float(lat), float(lon)
        if prev_lat is not None and _haversine_m(prev_lat, prev_lon, lat_f, lon_f) > max_gap_m:
            flush()

        point = {"latitude": lat_f, "longitude": lon_f}
        if "segment_id" in row.index:
            point["segment_id"] = row["segment_id"]
        rows.append(point)
        prev_lat, prev_lon = lat_f, lon_f

    flush()
    return runs


def _downsample(df: pd.DataFrame, max_points: int = 1500) -> pd.DataFrame:
    if len(df) <= max_points:
        return df
    step = max(1, len(df) // max_points)
    keep = list(range(0, len(df), step))
    if keep[-1] != len(df) - 1:
        keep.append(len(df) - 1)
    return df.iloc[keep]


def map_center_zoom(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    *,
    height_px: int = 420,
    width_px: int = 900,
    padding: float = 0.15,
) -> tuple[dict[str, float], float]:
    """Compute map center and zoom so the full route fits in the viewport."""
    lat_center = (lat_min + lat_max) / 2.0
    lon_center = (lon_min + lon_max) / 2.0
    lat_rad = math.radians(lat_center)

    lat_span = max(lat_max - lat_min, 1e-5) * (1.0 + padding)
    lon_span = max(lon_max - lon_min, 1e-5) * (1.0 + padding)
    lon_span *= max(math.cos(lat_rad), 0.2)

    lat_fraction = lat_span / 180.0
    lon_fraction = lon_span / 360.0
    world_px = 512.0
    zoom_lat = math.log2(height_px / world_px / max(lat_fraction, 1e-6))
    zoom_lon = math.log2(width_px / world_px / max(lon_fraction, 1e-6))
    zoom = min(zoom_lat, zoom_lon) - 0.35
    return {"lat": lat_center, "lon": lon_center}, max(5.0, min(16.0, zoom))


def build_gps_map(
    df: pd.DataFrame,
    *,
    title: str,
    route_label: str,
    segment_label: Callable[[int], str],
    start_label: str,
    end_label: str,
) -> go.Figure | None:
    runs = gps_runs(df)
    if not runs:
        return None

    all_points = pd.concat(runs, ignore_index=True)
    lat_min, lat_max = all_points["latitude"].min(), all_points["latitude"].max()
    lon_min, lon_max = all_points["longitude"].min(), all_points["longitude"].max()
    center, zoom = map_center_zoom(lat_min, lat_max, lon_min, lon_max)

    fig = go.Figure()
    colors = ("#2563eb", "#7c3aed", "#059669", "#dc2626", "#d97706")
    multi_segment = "segment_id" in all_points.columns and all_points["segment_id"].nunique() > 1

    for run_idx, run in enumerate(runs):
        run_line = _downsample(run)
        if len(run_line) < 2:
            continue
        if multi_segment and "segment_id" in run_line.columns:
            for seg_idx, seg_id in enumerate(run_line["segment_id"].unique()):
                seg = run_line[run_line["segment_id"] == seg_id]
                if len(seg) < 2:
                    continue
                label = segment_label(int(seg_id) + 1)
                color = colors[(run_idx + seg_idx) % len(colors)]
                fig.add_trace(
                    go.Scattermap(
                        lat=seg["latitude"],
                        lon=seg["longitude"],
                        mode="lines",
                        name=label,
                        line=dict(width=4, color=color),
                    )
                )
        else:
            label = route_label if len(runs) == 1 else f"{route_label} {run_idx + 1}"
            fig.add_trace(
                go.Scattermap(
                    lat=run_line["latitude"],
                    lon=run_line["longitude"],
                    mode="lines",
                    name=label,
                    line=dict(width=4, color=colors[run_idx % len(colors)]),
                )
            )

    start = all_points.iloc[0]
    end = all_points.iloc[-1]
    fig.add_trace(
        go.Scattermap(
            lat=[start["latitude"]],
            lon=[start["longitude"]],
            mode="markers",
            name=start_label,
            marker=dict(size=12, color="#16a34a", symbol="circle"),
        )
    )
    fig.add_trace(
        go.Scattermap(
            lat=[end["latitude"]],
            lon=[end["longitude"]],
            mode="markers",
            name=end_label,
            marker=dict(size=12, color="#dc2626", symbol="circle"),
        )
    )

    fig.update_layout(
        title=title,
        map=dict(style="open-street-map", center=center, zoom=zoom),
        height=420,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
