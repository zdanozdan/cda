import pandas as pd
import pytest

from cda_calc.map_plot import build_gps_map, gps_runs, map_center_zoom
from tests.synthetic import make_out_and_back_ride


def test_gps_runs_splits_on_missing_coords():
    df = pd.DataFrame(
        {
            "latitude": [52.0, 52.001, None, 52.1, 52.101],
            "longitude": [21.0, 21.001, None, 21.1, 21.101],
        }
    )
    runs = gps_runs(df)
    assert len(runs) == 2
    assert len(runs[0]) == 2
    assert len(runs[1]) == 2


def test_map_center_zoom_fits_route():
    center, zoom = map_center_zoom(52.40, 52.50, 16.85, 16.86)
    assert 52.44 < center["lat"] < 52.46
    assert 16.85 < center["lon"] < 16.86
    assert 8.0 <= zoom <= 14.0


def test_build_gps_map_from_synthetic_ride():
    df = make_out_and_back_ride(n_out=50, n_back=50)
    fig = build_gps_map(
        df,
        title="Route",
        route_label="Trasa",
        segment_label=lambda n: f"Fragment {n}",
        start_label="Start",
        end_label="End",
    )
    assert fig is not None
    assert fig.layout.map.center.lat is not None
    assert fig.layout.map.zoom is not None
