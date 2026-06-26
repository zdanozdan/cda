from __future__ import annotations

import numpy as np
import pandas as pd

from cda_calc.models import FilterStats


def apply_quality_mask(
    df: pd.DataFrame,
    min_speed_mps: float = 8.0,
    max_speed_mps: float | None = None,
    min_power_w: float = 150.0,
    max_accel_mps2: float | None = 0.5,
    accel: np.ndarray | None = None,
) -> tuple[pd.Series, FilterStats]:
    """
    Return boolean mask of points valid for CdA optimization.
    Invalid points are excluded from RMSE but may still appear on charts.
    """
    n_total = len(df)
    speed = df["speed_mps"].to_numpy(dtype=float)
    power = df["power_w"].to_numpy(dtype=float)

    valid = np.ones(n_total, dtype=bool)
    rejected_low_speed = 0
    rejected_high_speed = 0
    rejected_low_power = 0
    rejected_high_accel = 0

    low_speed = np.isnan(speed) | (speed < min_speed_mps)
    rejected_low_speed = int(low_speed.sum())
    valid &= ~low_speed

    if max_speed_mps is not None:
        high_speed = np.isnan(speed) | (speed > max_speed_mps)
        rejected_high_speed = int(high_speed.sum())
        valid &= ~high_speed

    low_power = np.isnan(power) | (power < min_power_w)
    rejected_low_power = int(low_power.sum())
    valid &= ~low_power

    if max_accel_mps2 is not None and accel is not None:
        high_accel = np.abs(accel) > max_accel_mps2
        rejected_high_accel = int(high_accel.sum())
        valid &= ~high_accel

    n_valid = int(valid.sum())
    pct_valid = 100.0 * n_valid / n_total if n_total else 0.0

    stats = FilterStats(
        n_total=n_total,
        n_valid=n_valid,
        pct_valid=pct_valid,
        rejected_low_speed=rejected_low_speed,
        rejected_high_speed=rejected_high_speed,
        rejected_low_power=rejected_low_power,
        rejected_high_accel=rejected_high_accel,
    )
    return pd.Series(valid, index=df.index, name="valid"), stats
