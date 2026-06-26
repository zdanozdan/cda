from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from cda_calc.filters import apply_quality_mask
from cda_calc.models import AnalysisParams, AnalysisResult
from cda_calc.physics import (
    align_ve_to_measured,
    compute_acceleration,
    compute_dt_seconds,
    rmse_ve,
    smooth_speed,
    virtual_elevation,
)


def prepare_segment(df: pd.DataFrame, params: AnalysisParams) -> tuple[pd.DataFrame, np.ndarray, pd.Series]:
    dt = compute_dt_seconds(df["timestamp"])
    speed_smooth = smooth_speed(df["speed_mps"].to_numpy(dtype=float), dt)
    accel = compute_acceleration(speed_smooth, dt)
    valid_mask, stats = apply_quality_mask(
        df,
        min_speed_mps=params.min_speed_mps,
        max_speed_mps=params.max_speed_mps,
        min_power_w=params.min_power_w,
        max_accel_mps2=params.max_accel_mps2,
        accel=accel,
    )
    return df, accel, valid_mask


def optimize_cda(
    df: pd.DataFrame,
    params: AnalysisParams,
    cda_bounds: tuple[float, float] = (0.15, 0.35),
) -> AnalysisResult:
    _, accel, valid_mask = prepare_segment(df, params)
    _, filter_stats = apply_quality_mask(
        df,
        min_speed_mps=params.min_speed_mps,
        max_speed_mps=params.max_speed_mps,
        min_power_w=params.min_power_w,
        max_accel_mps2=params.max_accel_mps2,
        accel=accel,
    )

    measured = df["elevation_m"]

    def cost(cda: float) -> float:
        trial = AnalysisParams(**{**params.__dict__, "cda": cda})
        ve = virtual_elevation(df, trial)
        return rmse_ve(ve, measured, valid_mask)

    result = minimize_scalar(cost, bounds=cda_bounds, method="bounded")
    cda_opt = float(result.x)
    final_params = AnalysisParams(**{**params.__dict__, "cda": cda_opt})
    ve = virtual_elevation(df, final_params)
    ve_aligned = align_ve_to_measured(ve, measured, valid_mask)
    residuals = ve_aligned - measured
    rmse = float(result.fun)

    return AnalysisResult(
        cda_optimal=cda_opt,
        rmse=rmse,
        coverage_pct=filter_stats.pct_valid,
        ve_profile=ve_aligned,
        residuals=residuals,
        valid_mask=valid_mask,
        filter_stats=filter_stats,
        params_used=final_params,
    )


def compute_ve_with_cda(df: pd.DataFrame, params: AnalysisParams) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return aligned VE, residuals, valid_mask for manual CdA slider."""
    _, accel, valid_mask = prepare_segment(df, params)
    ve = virtual_elevation(df, params)
    measured = df["elevation_m"]
    ve_aligned = align_ve_to_measured(ve, measured, valid_mask)
    residuals = ve_aligned - measured
    return ve_aligned, residuals, valid_mask
