"""Synthetic ride data for unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from cda_calc.models import AnalysisParams
from cda_calc.physics import G, compute_acceleration, compute_dt_seconds, smooth_speed, virtual_elevation

TRUE_CDA = 0.22


def make_out_and_back_ride(
    n_out: int = 120,
    n_back: int = 120,
    dt_s: float = 1.0,
    true_cda: float = TRUE_CDA,
    params: AnalysisParams | None = None,
    include_artifacts: bool = True,
) -> pd.DataFrame:
    """
    Build synthetic out-and-back: known elevation profile, power derived from physics.
    Inserts low-power / low-speed points at turnaround for filter tests.
    """
    if params is None:
        params = AnalysisParams(cda=true_cda)

    n = n_out + n_back
    timestamps = [datetime(2024, 6, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=i * dt_s) for i in range(n)]

    # Elevation: gentle climb out, gentle descent back
    elev = np.zeros(n)
    for i in range(n_out):
        elev[i] = 100.0 + 0.05 * i
    peak = elev[n_out - 1]
    for j in range(n_back):
        elev[n_out + j] = peak - 0.05 * j

    speed = np.full(n, 11.0)  # ~40 km/h
    power = np.full(n, 280.0)

    # Turnaround artifacts: low speed + low power (zakręt / zwrot)
    turnaround = slice(max(0, n_out - 3), min(n, n_out + 3))
    speed[turnaround] = 5.0
    power[turnaround] = 80.0

    lat_start, lon_start = 52.1, 21.0
    latitudes = []
    longitudes = []
    distance = [0.0]
    for i in range(n):
        if i < n_out:
            latitudes.append(lat_start + i * 0.0001)
            longitudes.append(lon_start + i * 0.0001)
        else:
            k = i - n_out
            latitudes.append(lat_start + (n_out - k) * 0.0001)
            longitudes.append(lon_start + (n_out - k) * 0.0001)
        if i > 0:
            distance.append(distance[-1] + speed[i] * dt_s)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "latitude": latitudes,
            "longitude": longitudes,
            "elevation_m": elev,
            "power_w": power,
            "speed_mps": speed,
            "distance_m": distance,
            "cadence": np.full(n, 90.0),
            "heart_rate": np.full(n, 150.0),
        }
    )

    # Derive power from known physics (same smoothing/accel as VE engine)
    m, rho, crr, cda = params.mass_kg, params.air_density, params.crr, true_cda
    dt = compute_dt_seconds(df["timestamp"])
    speed_arr = df["speed_mps"].to_numpy(dtype=float)
    speed_smooth = smooth_speed(speed_arr, dt)
    accel = compute_acceleration(speed_smooth, dt)
    derived_power = []
    for i in range(n):
        v = max(speed_smooth[i], 0.1)
        if i == 0:
            slope = (elev[1] - elev[0]) / (v * dt[1]) if len(elev) > 1 else 0.0
        else:
            slope = (elev[i] - elev[i - 1]) / (v * dt[i])
        p = m * G * v * (slope + crr + accel[i] / G + (rho * cda * v**2) / (2 * m * G))
        derived_power.append(p / (1 - params.drivetrain_loss_pct / 100.0))

    df["power_w"] = derived_power
    if include_artifacts:
        df.loc[turnaround, "speed_mps"] = 5.0
        df.loc[turnaround, "power_w"] = 80.0

    return df


def verify_ve_matches(df: pd.DataFrame, params: AnalysisParams, valid_mask: pd.Series | None = None) -> float:
    from cda_calc.physics import align_ve_to_measured, rmse_ve

    if valid_mask is None:
        valid_mask = pd.Series(True, index=df.index)
    ve = virtual_elevation(df, params)
    return rmse_ve(ve, df["elevation_m"], valid_mask)
