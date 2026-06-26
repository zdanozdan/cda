from pathlib import Path
from dataclasses import replace

import pandas as pd
import pytest

from cda_calc.garmin_splits import (
    align_laps_to_ride,
    average_temperature_c,
    lap_label,
    parse_duration_to_seconds,
    parse_garmin_splits_csv,
    selected_lap_ranges,
)
from cda_calc.segment import slice_ride_km_ranges
from cda_calc.tcx_parser import parse_tcx
from tests.synthetic import make_out_and_back_ride

FIXTURE = Path(__file__).parent / "fixtures" / "garmin_splits_pl.csv"


def test_parse_duration_formats():
    assert parse_duration_to_seconds("7:55.3") == pytest.approx(475.3)
    assert parse_duration_to_seconds("1:04:11") == 3851
    assert parse_duration_to_seconds("12:47") == 767
    assert parse_duration_to_seconds("3:45:55") == 13555


def test_parse_garmin_splits_pl_csv():
    laps = parse_garmin_splits_csv(FIXTURE)
    assert len(laps) == 26
    assert laps[0].number == 1
    assert laps[0].km_start == pytest.approx(0.0)
    assert laps[0].km_end == pytest.approx(5.0)
    assert laps[-1].km_end == pytest.approx(124.0, abs=0.02)
    assert laps[22].distance_km == pytest.approx(1.14)
    assert laps[0].avg_power_w == pytest.approx(207.0)
    assert laps[0].avg_temp_c == pytest.approx(25.1)
    assert laps[1].avg_temp_c == pytest.approx(24.9)


def test_average_temperature_c_weighted_by_duration():
    laps = parse_garmin_splits_csv(FIXTURE)
    assert average_temperature_c(laps, [1, 2]) == pytest.approx(25.0, abs=0.05)
    assert average_temperature_c(laps, [1]) == pytest.approx(25.1)


def test_average_temperature_c_missing_column():
    laps = parse_garmin_splits_csv(FIXTURE)
    laps_no_temp = [replace(lap, avg_temp_c=None) for lap in laps[:2]]
    assert average_temperature_c(laps_no_temp) is None


def test_align_laps_scales_to_ride_distance():
    laps = parse_garmin_splits_csv(FIXTURE)
    aligned = align_laps_to_ride(laps, ride_total_km=100.0)
    assert aligned[-1].km_end == pytest.approx(100.0, rel=1e-6)
    assert aligned[0].km_end == pytest.approx(100.0 * 5.0 / 124.01, rel=0.01)


def test_selected_lap_ranges_preserves_order():
    laps = parse_garmin_splits_csv(FIXTURE)
    ranges = selected_lap_ranges(laps, [3, 1, 2])
    assert ranges == [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0)]


def test_riding_duration_ignores_lap_gaps():
    from datetime import timedelta

    from cda_calc.segment import riding_duration_seconds

    df = make_out_and_back_ride(n_out=5, n_back=5)
    lap_a = df.iloc[:5].copy()
    lap_b = df.iloc[5:10].copy()
    lap_b["timestamp"] = lap_b["timestamp"] + timedelta(hours=2)
    combined = pd.concat([lap_a, lap_b], ignore_index=True)
    wall = (combined["timestamp"].iloc[-1] - combined["timestamp"].iloc[0]).total_seconds()
    riding = riding_duration_seconds(combined)
    assert riding < wall
    assert riding == pytest.approx(9.0, abs=1.0)


def test_slice_ride_km_ranges_concatenates_laps():
    df = make_out_and_back_ride(n_out=200, n_back=200)
    df["distance_m"] = df.index * 50.0
    ranges = [(1.0, 2.0), (4.0, 5.0)]
    segment = slice_ride_km_ranges(df, ranges)
    assert len(segment) >= 40
    assert segment["distance_m"].iloc[0] == pytest.approx(1000.0)
    assert lap_label(parse_garmin_splits_csv(FIXTURE)[0]).startswith("Okr. 1:")
