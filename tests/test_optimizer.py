import pandas as pd

from cda_calc.filters import apply_quality_mask
from cda_calc.models import AnalysisParams
from cda_calc.optimizer import optimize_cda
from cda_calc.physics import compute_acceleration, compute_dt_seconds, rmse_ve, smooth_speed, virtual_elevation
from tests.synthetic import TRUE_CDA, make_out_and_back_ride


def test_optimizer_recovers_cda_out_and_back():
    params = AnalysisParams(cda=0.25, crr=0.00249, min_speed_mps=8.0, min_power_w=150.0)
    df = make_out_and_back_ride(n_out=150, n_back=150)
    result = optimize_cda(df, params)
    assert abs(result.cda_optimal - TRUE_CDA) < 0.02
    assert result.rmse < 1.0
    assert result.coverage_pct >= 30.0


def test_without_filters_rmse_worse_on_bad_segments():
    params = AnalysisParams(cda=TRUE_CDA, crr=0.00249)
    df = make_out_and_back_ride()
    all_mask = pd.Series(True, index=df.index)
    bad_mask = pd.Series(False, index=df.index)
    ve = virtual_elevation(df, params)
    rmse_all = rmse_ve(ve, df["elevation_m"], all_mask)
    rmse_bad = rmse_ve(ve, df["elevation_m"], bad_mask)
    assert rmse_bad == float("inf")
    assert rmse_all < 5.0


def test_filter_improves_optimization_stability():
    df = make_out_and_back_ride()
    loose = AnalysisParams(cda=0.25, min_speed_mps=0.0, min_power_w=0.0, max_accel_mps2=None)
    strict = AnalysisParams(cda=0.25, min_speed_mps=8.0, min_power_w=150.0)
    r_loose = optimize_cda(df, loose)
    r_strict = optimize_cda(df, strict)
    assert abs(r_strict.cda_optimal - TRUE_CDA) <= abs(r_loose.cda_optimal - TRUE_CDA) + 0.01
