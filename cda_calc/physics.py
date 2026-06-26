from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from cda_calc.models import AnalysisParams

G = 9.81


def air_density_kg_m3(
    temperature_c: float,
    altitude_m: float,
    relative_humidity_pct: float = 50.0,
) -> float:
    """Approximate moist air density at altitude (ISA-style)."""
    t_k = temperature_c + 273.15
    p0 = 101325.0 * np.exp(-altitude_m / 8500.0)
    # Magnus formula for saturation vapor pressure (Pa)
    e_s = 610.94 * np.exp(17.625 * temperature_c / (temperature_c + 243.04))
    e = (relative_humidity_pct / 100.0) * e_s
    r_d = 287.058
    r_v = 461.495
    return (p0 - e) / (r_d * t_k) + e / (r_v * t_k)


def compute_dt_seconds(timestamps: pd.Series) -> np.ndarray:
    ts = pd.to_datetime(timestamps)
    dt = ts.diff().dt.total_seconds().to_numpy(dtype=float).copy()
    dt[0] = dt[1] if len(dt) > 1 and not np.isnan(dt[1]) else 1.0
    dt = np.where((dt <= 0) | np.isnan(dt), np.nanmedian(dt[dt > 0]) if np.any(dt > 0) else 1.0, dt)
    return dt


def smooth_speed(speed_mps: np.ndarray, dt: np.ndarray, window_seconds: float = 5.0) -> np.ndarray:
    if len(speed_mps) < 5:
        return speed_mps.copy()
    median_dt = float(np.nanmedian(dt))
    window = max(5, int(round(window_seconds / median_dt)))
    if window % 2 == 0:
        window += 1
    if window >= len(speed_mps):
        window = len(speed_mps) - 1 if len(speed_mps) % 2 == 0 else len(speed_mps)
    if window < 5:
        return speed_mps.copy()
    filled = pd.Series(speed_mps).interpolate(limit_direction="both").to_numpy()
    return savgol_filter(filled, window_length=window, polyorder=2)


def compute_acceleration(speed_mps: np.ndarray, dt: np.ndarray) -> np.ndarray:
    n = len(speed_mps)
    accel = np.zeros(n)
    for i in range(n):
        if i == 0:
            accel[i] = (speed_mps[1] - speed_mps[0]) / dt[0] if n > 1 else 0.0
        elif i == n - 1:
            accel[i] = (speed_mps[-1] - speed_mps[-2]) / dt[-1]
        else:
            denom = dt[i - 1] + dt[i]
            accel[i] = (speed_mps[i + 1] - speed_mps[i - 1]) / denom if denom > 0 else 0.0
    return accel


def mechanical_power(power_w: np.ndarray, drivetrain_loss_pct: float) -> np.ndarray:
    factor = 1.0 - drivetrain_loss_pct / 100.0
    return power_w * factor


def virtual_elevation(
    df: pd.DataFrame,
    params: AnalysisParams,
) -> pd.Series:
    """
    Compute virtual elevation profile using Chung method.
    Handles non-contiguous segments if 'segment_id' column is present.
    Returns Series aligned with df index.
    """
    # If no segment_id, treat as one segment
    if "segment_id" not in df.columns:
        df = df.copy()
        df["segment_id"] = 0

    ve_full = pd.Series(index=df.index, dtype=float, name="ve_m")

    for _, seg_df in df.groupby("segment_id", sort=False):
        dt = compute_dt_seconds(seg_df["timestamp"])
        speed = smooth_speed(seg_df["speed_mps"].to_numpy(dtype=float), dt)
        accel = compute_acceleration(speed, dt)
        power = mechanical_power(seg_df["power_w"].to_numpy(dtype=float), params.drivetrain_loss_pct)

        m = params.mass_kg
        rho = params.air_density
        crr = params.crr
        cda = params.cda

        ve = np.zeros(len(seg_df))
        h0 = float(seg_df["elevation_m"].iloc[0]) if pd.notna(seg_df["elevation_m"].iloc[0]) else 0.0
        ve[0] = h0

        for i in range(1, len(seg_df)):
            v = max(speed[i], 0.1)
            p = power[i]
            a = accel[i]
            if np.isnan(p) or np.isnan(v):
                ve[i] = ve[i - 1]
                continue
            slope = p / (m * G * v) - crr - a / G - (rho * cda * v**2) / (2 * m * G)
            dh = slope * v * dt[i]
            ve[i] = ve[i - 1] + dh
        
        ve_full.loc[seg_df.index] = ve

    return ve_full


def align_ve_to_measured(ve: pd.Series, measured: pd.Series, valid_mask: pd.Series) -> pd.Series:
    """
    Align VE to measured elevation by minimizing error per segment.
    If multiple segments exist (non-contiguous), each is aligned independently
    to account for barometric drift between segments.
    """
    # We need segment info. If not available in ve.index (it's not), 
    # we might need to pass it or infer it.
    # Actually, we can use the valid_mask to find contiguous blocks, 
    # but it's better if we know the segments.
    
    # Let's assume we can't easily get segment_id here without changing signature.
    # BUT, we can detect jumps in index or use a global segment detector.
    # Wait, the best way is to pass the segment_ids.
    
    # Let's check if we can infer segments from gaps in index or time.
    # Or better, let's just align the whole thing if we don't have segment info.
    # But we WANT to align per segment.
    
    # Let's look at how this is called. It's called with ve, measured, valid_mask.
    # All three are Series with the same index.
    
    # If the index has gaps, we can use that.
    
    aligned = ve.copy()
    
    # Simple segment detector: jumps in index > 1
    idx = ve.index.to_series()
    gaps = idx.diff() > 1
    segment_starts = idx[gaps | (idx == idx.iloc[0])]
    
    for i in range(len(segment_starts)):
        start = segment_starts.iloc[i]
        end = segment_starts.iloc[i+1] if i+1 < len(segment_starts) else idx.iloc[-1] + 1
        
        seg_mask = (idx >= start) & (idx < end)
        seg_valid = valid_mask & seg_mask
        
        if not seg_valid.any():
            continue
            
        # Align this segment by its first valid point
        first_valid = seg_valid[seg_valid].index[0]
        offset = float(measured.loc[first_valid]) - float(ve.loc[first_valid])
        aligned.loc[seg_mask] = ve.loc[seg_mask] + offset
        
    return aligned


def rmse_ve(
    ve: pd.Series,
    measured: pd.Series,
    valid_mask: pd.Series,
) -> float:
    aligned = align_ve_to_measured(ve, measured, valid_mask)
    valid = valid_mask & measured.notna() & aligned.notna()
    if not valid.any():
        return float("inf")
    diff = aligned[valid] - measured[valid]
    return float(np.sqrt(np.mean(diff**2)))


def _power_segments(
    power: np.ndarray,
    dt: np.ndarray,
    max_gap_s: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Split power stream at long recording gaps; trim invalid samples."""
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    start = 0
    for i in range(1, len(power)):
        if dt[i] > max_gap_s:
            if i > start:
                segments.append((power[start:i], dt[start:i]))
            start = i
    if start < len(power):
        segments.append((power[start:], dt[start:]))

    cleaned: list[tuple[np.ndarray, np.ndarray]] = []
    for p_seg, dt_seg in segments:
        valid = np.isfinite(p_seg)
        if not valid.any():
            continue
        first = int(np.argmax(valid))
        last = int(len(p_seg) - 1 - np.argmax(valid[::-1]))
        cleaned.append((p_seg[first : last + 1], dt_seg[first : last + 1]))
    return cleaned


def normalized_power(
    power_w: np.ndarray,
    dt: np.ndarray,
    window_s: float = 30.0,
    max_gap_s: float = 60.0,
    max_weight_dt_s: float = 5.0,
) -> float:
    """TrainingPeaks-style Normalized Power (30 s rolling avg → ^4 → mean → ^¼)."""
    power = np.asarray(power_w, dtype=float)
    dt = np.asarray(dt, dtype=float)
    if len(power) == 0:
        return float("nan")
    if len(power) == 1 and np.isfinite(power[0]):
        return float(power[0])

    raised_chunks: list[np.ndarray] = []
    weight_chunks: list[np.ndarray] = []

    for p_seg, dt_seg in _power_segments(power, dt, max_gap_s):
        filled = pd.Series(p_seg).interpolate(limit_direction="both").to_numpy(dtype=float)
        dt_seg = np.clip(dt_seg, 0.0, max_weight_dt_s)
        if len(filled) == 1:
            raised_chunks.append(np.array([filled[0] ** 4]))
            weight_chunks.append(dt_seg)
            continue

        t = np.cumsum(dt_seg)
        rolling = np.empty(len(filled), dtype=float)
        start = 0
        for i in range(len(filled)):
            while start < i and t[start] < t[i] - window_s:
                start += 1
            rolling[i] = np.average(filled[start : i + 1], weights=dt_seg[start : i + 1])
        raised_chunks.append(np.power(rolling, 4))
        weight_chunks.append(dt_seg)

    if not raised_chunks:
        return float("nan")

    raised = np.concatenate(raised_chunks)
    weights = np.concatenate(weight_chunks)
    if weights.sum() <= 0:
        return float("nan")
    return float(np.average(raised, weights=weights) ** 0.25)


def power_saved_watts(delta_cda: float, speed_kph: float, air_density: float) -> float:
    v = speed_kph / 3.6
    return 0.5 * air_density * delta_cda * v**3


def steady_flat_power_w(
    cda_m2: float,
    mass_kg: float,
    speed_kph: float = 40.0,
    crr: float = 0.0026,
    air_density: float = 1.225,
    drivetrain_loss_pct: float = 2.0,
) -> float:
    """Crank power (W) to hold speed on flat road with no wind."""
    v = speed_kph / 3.6
    p_wheel = crr * mass_kg * G * v + 0.5 * air_density * cda_m2 * v**3
    return p_wheel / (1.0 - drivetrain_loss_pct / 100.0)


def steady_flat_speed_mps(
    cda_m2: float,
    mass_kg: float,
    power_w: float,
    crr: float = 0.0026,
    air_density: float = 1.225,
    drivetrain_loss_pct: float = 2.0,
) -> float:
    """Speed (m/s) on flat road at given crank power with no wind."""
    p_wheel = power_w * (1.0 - drivetrain_loss_pct / 100.0)
    if p_wheel <= 0:
        return 0.0

    def residual(v: float) -> float:
        return crr * mass_kg * G * v + 0.5 * air_density * cda_m2 * v**3 - p_wheel

    lo, hi = 0.1, 40.0
    if residual(lo) >= 0:
        return lo
    if residual(hi) <= 0:
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if residual(mid) <= 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def steady_flat_speed_kph(
    cda_m2: float,
    mass_kg: float,
    power_w: float,
    crr: float = 0.0026,
    air_density: float = 1.225,
    drivetrain_loss_pct: float = 2.0,
) -> float:
    return steady_flat_speed_mps(
        cda_m2,
        mass_kg,
        power_w,
        crr=crr,
        air_density=air_density,
        drivetrain_loss_pct=drivetrain_loss_pct,
    ) * 3.6
