import numpy as np
import pandas as pd

from cda_calc.filters import apply_quality_mask
from tests.synthetic import make_out_and_back_ride


def test_filter_stats_counts():
    df = make_out_and_back_ride()
    mask, stats = apply_quality_mask(df, min_speed_mps=8.0, min_power_w=150.0)
    assert stats.n_total == len(df)
    assert stats.n_valid == int(mask.sum())
    assert stats.pct_valid == 100.0 * stats.n_valid / stats.n_total


def test_filter_rejects_high_speed():
    df = make_out_and_back_ride()
    mask, stats = apply_quality_mask(df, min_speed_mps=0.0, max_speed_mps=5.0, min_power_w=0.0)
    assert stats.rejected_high_speed > 0
    assert stats.n_valid < stats.n_total


def test_all_invalid_when_thresholds_absurd():
    df = make_out_and_back_ride()
    mask, stats = apply_quality_mask(df, min_speed_mps=50.0, min_power_w=5000.0)
    assert stats.n_valid == 0
    assert not mask.any()
