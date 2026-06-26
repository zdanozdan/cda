import numpy as np
import pandas as pd
import pytest

from cda_calc.filters import apply_quality_mask
from cda_calc.models import AnalysisParams
from cda_calc.physics import air_density_kg_m3, compute_acceleration, compute_dt_seconds, normalized_power, power_saved_watts, smooth_speed, steady_flat_power_w, steady_flat_speed_kph, virtual_elevation
from tests.synthetic import TRUE_CDA, make_out_and_back_ride, verify_ve_matches


def test_air_density_decreases_with_altitude():
    low = air_density_kg_m3(15.0, 0.0)
    high = air_density_kg_m3(15.0, 1000.0)
    assert high < low < 1.3


def test_virtual_elevation_known_cda_low_rmse():
    params = AnalysisParams(cda=TRUE_CDA)
    df = make_out_and_back_ride(include_artifacts=False, params=params)
    mask = pd.Series(True, index=df.index)
    rmse = verify_ve_matches(df, params, mask)
    assert rmse < 0.15


def test_filters_exclude_low_speed_and_power():
    df = make_out_and_back_ride()
    dt = compute_dt_seconds(df["timestamp"])
    speed = smooth_speed(df["speed_mps"].to_numpy(), dt)
    accel = compute_acceleration(speed, dt)
    mask, stats = apply_quality_mask(df, min_speed_mps=8.0, min_power_w=150.0, accel=accel)
    assert stats.n_valid < stats.n_total
    assert stats.rejected_low_speed > 0 or stats.rejected_low_power > 0
    assert stats.pct_valid >= 30.0


def test_power_saved_watts_positive():
    saved = power_saved_watts(0.01, 40.0, 1.225)
    assert saved > 0


def test_steady_flat_power_w_pro_tt_range():
    p_lo = steady_flat_power_w(0.17, 70.0, crr=0.0026)
    p_hi = steady_flat_power_w(0.20, 70.0, crr=0.0026)
    assert p_lo == pytest.approx(166, abs=2)
    assert p_hi == pytest.approx(192, abs=2)
    assert p_lo < p_hi


def test_steady_flat_power_w_increases_with_cda():
    low_cda = steady_flat_power_w(0.20, 70.0)
    high_cda = steady_flat_power_w(0.30, 70.0)
    assert high_cda > low_cda


def test_steady_flat_speed_inverts_power():
    cda = 0.24
    mass = 70.0
    power = steady_flat_power_w(cda, mass, speed_kph=38.0)
    speed = steady_flat_speed_kph(cda, mass, power)
    assert speed == pytest.approx(38.0, abs=0.05)


def test_steady_flat_speed_lower_cda_is_faster_at_same_power():
    power = 250.0
    fast = steady_flat_speed_kph(0.22, 70.0, power)
    slow = steady_flat_speed_kph(0.28, 70.0, power)
    assert fast > slow


def test_normalized_power_constant():
    power = np.full(60, 200.0)
    dt = np.ones(60)
    assert normalized_power(power, dt) == pytest.approx(200.0, rel=1e-3)


def test_normalized_power_above_average_when_variable():
    power = np.concatenate([np.full(40, 100.0), np.full(40, 300.0)])
    dt = np.ones(80)
    np_val = normalized_power(power, dt)
    assert np_val > power.mean()


def test_normalized_power_ignores_long_gaps():
    power = np.concatenate([np.full(300, 200.0), np.array([0.0, 0.0])])
    dt = np.concatenate([np.ones(300), np.array([12_000.0, 1.0])])
    np_val = normalized_power(power, dt)
    assert np_val == pytest.approx(200.0, rel=0.02)