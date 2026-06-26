"""Segment selection helpers (distance km ↔ row indices)."""

from __future__ import annotations

import math

import pandas as pd


def total_distance_km(df_full: pd.DataFrame) -> float:
    if df_full.empty:
        return 0.0
    distances = pd.to_numeric(df_full["distance_m"], errors="coerce").dropna()
    if distances.empty:
        return 0.0
    last = float(distances.iloc[-1])
    if not math.isfinite(last) or last < 0:
        return 0.0
    return last / 1000.0


def clamp_segment_km(
    km_start: float,
    km_end: float,
    total_km: float,
    *,
    min_span_km: float = 0.05,
) -> tuple[float, float]:
    """Return sorted, finite segment bounds within ``[0, total_km]``."""
    total = max(float(total_km), min_span_km)
    start = 0.0 if not math.isfinite(km_start) else float(km_start)
    end = total if not math.isfinite(km_end) else float(km_end)
    start = max(0.0, min(start, total))
    end = max(0.0, min(end, total))
    if end < start:
        start, end = end, start
    if end - start < min_span_km:
        end = min(total, start + min_span_km)
        start = max(0.0, end - min_span_km)
    return start, end


def km_range_to_indices(
    df_full: pd.DataFrame,
    km_start: float,
    km_end: float,
) -> tuple[int, int]:
    lo_km, hi_km = min(km_start, km_end), max(km_start, km_end)
    d = df_full["distance_m"].to_numpy()
    start = int(pd.Series(d).searchsorted(lo_km * 1000.0, side="left"))
    end = int(pd.Series(d).searchsorted(hi_km * 1000.0, side="right")) - 1
    start = max(0, min(start, len(df_full) - 1))
    end = max(start, min(end, len(df_full) - 1))
    return start, end


def indices_to_km_range(df_full: pd.DataFrame, start: int, end: int) -> tuple[float, float]:
    km0 = float(df_full.at[start, "distance_m"] / 1000.0)
    km1 = float(df_full.at[end, "distance_m"] / 1000.0)
    return min(km0, km1), max(km0, km1)


def riding_duration_seconds(df: pd.DataFrame, max_dt_s: float = 30.0) -> float:
    """Sum of inter-point Δt, ignoring long gaps (lap boundaries, postoje)."""
    if len(df) < 2:
        return 0.0
    dts = pd.to_datetime(df["timestamp"]).diff().dt.total_seconds().dropna()
    return float(dts[(dts > 0) & (dts <= max_dt_s)].sum())


def slice_ride_km_ranges(df_full: pd.DataFrame, km_ranges: list[tuple[float, float]]) -> pd.DataFrame:
    """Concatenate one or more km sub-ranges (e.g. selected Garmin laps)."""
    from cda_calc.tcx_parser import slice_ride

    if not km_ranges:
        raise ValueError("Brak zakresów km do wycięcia.")

    parts: list[pd.DataFrame] = []
    for i, (km_start, km_end) in enumerate(km_ranges):
        start_idx, end_idx = km_range_to_indices(df_full, km_start, km_end)
        part = slice_ride(df_full, start_idx, end_idx).copy()
        part["segment_id"] = i
        parts.append(part)
    if len(parts) == 1:
        return parts[0]
    return pd.concat(parts, ignore_index=False)


def extract_km_range_from_relayout(event: dict | None) -> tuple[float, float] | None:
    """Parse Plotly relayout / component payload → (km_start, km_end)."""
    if not event or not isinstance(event, dict):
        return None

    km_start = event.get("km_start")
    km_end = event.get("km_end")
    if km_start is not None and km_end is not None:
        lo, hi = float(km_start), float(km_end)
        if hi - lo < 0.05:
            return None
        return min(lo, hi), max(lo, hi)

    xs: list[float] = []
    x0 = event.get("shapes[0].x0")
    x1 = event.get("shapes[0].x1")
    if x0 is not None and x1 is not None:
        xs.extend([float(x0), float(x1)])
    shapes = event.get("shapes")
    if isinstance(shapes, list) and shapes and isinstance(shapes[0], dict):
        s0 = shapes[0].get("x0")
        s1 = shapes[0].get("x1")
        if s0 is not None and s1 is not None:
            xs.extend([float(s0), float(s1)])

    if len(xs) < 2:
        return None
    lo, hi = min(xs), max(xs)
    if hi - lo < 0.05:
        return None
    return lo, hi


def extract_km_range_from_plotly_selection(event) -> tuple[float, float] | None:
    """Parse Streamlit/Plotly selection event → (km_start, km_end)."""
    if event is None:
        return None

    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    if selection is None:
        return None

    def _get(name: str):
        val = getattr(selection, name, None)
        if val is None and isinstance(selection, dict):
            val = selection.get(name)
        return val

    xs: list[float] = []

    for p in _get("points") or []:
        if not isinstance(p, dict):
            continue
        if p.get("x") is not None:
            xs.append(float(p["x"]))

    for box in _get("box") or []:
        if not isinstance(box, dict):
            continue
        x0, x1 = box.get("x0"), box.get("x1")
        if x0 is not None and x1 is not None:
            xs.extend([float(x0), float(x1)])

    for lasso in _get("lasso") or []:
        if not isinstance(lasso, dict):
            continue
        if lasso.get("x") is not None:
            xs.append(float(lasso["x"]))

    if len(xs) < 2:
        return None

    lo, hi = min(xs), max(xs)
    if hi - lo < 0.05:
        return None
    return lo, hi


def extract_indices_from_plotly_selection(
    df_full: pd.DataFrame,
    event,
) -> tuple[int, int] | None:
    km_range = extract_km_range_from_plotly_selection(event)
    if km_range is not None:
        return km_range_to_indices(df_full, *km_range)

    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    if selection is None:
        return None

    row_indices: list[int] = []
    point_indices = getattr(selection, "point_indices", None)
    if point_indices is None and isinstance(selection, dict):
        point_indices = selection.get("point_indices")
    if point_indices:
        row_indices.extend(int(i) for i in point_indices)

    for p in getattr(selection, "points", None) or []:
        if isinstance(p, dict):
            for key in ("point_index", "pointIndex", "point_number"):
                if key in p and p[key] is not None:
                    row_indices.append(int(p[key]))
                    break

    if len(row_indices) >= 2:
        start, end = min(row_indices), max(row_indices)
        if end > start:
            return start, end
    return None
