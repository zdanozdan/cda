from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd


@dataclass
class TirePreset:
    name: str
    size_mm: int
    pressure_psi: int
    crr: float
    estimated: bool = False


@dataclass
class RideData:
    df: pd.DataFrame
    speed_source: Literal["sensor", "gps", "mixed"]
    has_power: bool
    laps: list[dict] = field(default_factory=list)
    filename: str = ""


@dataclass
class AnalysisParams:
    mass_kg: float = 74.0
    crr: float = 0.0026
    cda: float = 0.22
    air_density: float = 1.225
    drivetrain_loss_pct: float = 2.0
    min_speed_mps: float = 8.0
    max_speed_mps: float | None = None
    min_power_w: float = 150.0
    max_accel_mps2: float | None = 0.5
    min_coverage_pct: float = 30.0


@dataclass
class FilterStats:
    n_total: int
    n_valid: int
    pct_valid: float
    rejected_low_speed: int
    rejected_low_power: int
    rejected_high_speed: int = 0
    rejected_high_accel: int = 0


@dataclass
class AnalysisResult:
    cda_optimal: float
    rmse: float
    coverage_pct: float
    ve_profile: pd.Series
    residuals: pd.Series
    valid_mask: pd.Series
    filter_stats: FilterStats
    params_used: AnalysisParams
