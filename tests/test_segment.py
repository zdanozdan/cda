import pandas as pd

from cda_calc.segment import (
    analysis_segment_boundaries_km,
    build_analysis_distance_m,
    clamp_segment_km,
    extract_indices_from_plotly_selection,
    extract_km_range_from_plotly_selection,
    extract_km_range_from_relayout,
    km_range_to_indices,
    total_distance_km,
)


def _sample_df(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "distance_m": [i * 100.0 for i in range(n)],
            "power_w": [200.0] * n,
            "speed_mps": [10.0] * n,
        }
    )


def test_km_range_to_indices():
    df = _sample_df()
    start, end = km_range_to_indices(df, 2.0, 5.0)
    assert start == 20
    assert end == 50


def test_total_distance_km_ignores_nan_tail():
    df = _sample_df()
    df.loc[df.index[-1], "distance_m"] = float("nan")
    assert total_distance_km(df) == 9.8


def test_clamp_segment_km_handles_nan():
    assert clamp_segment_km(0.0, float("nan"), 10.0) == (0.0, 10.0)
    assert clamp_segment_km(float("nan"), 5.0, 10.0) == (0.0, 5.0)


def test_clamp_segment_km_sorts_and_clips():
    assert clamp_segment_km(8.0, 2.0, 10.0) == (2.0, 8.0)
    assert clamp_segment_km(-1.0, 12.0, 10.0) == (0.0, 10.0)


def test_extract_km_from_relayout_payload():
    km = extract_km_range_from_relayout({"km_start": 3.5, "km_end": 8.0, "source": "shape"})
    assert km == (3.5, 8.0)


def test_extract_km_from_relayout_shape_keys():
    km = extract_km_range_from_relayout({"shapes[0].x0": 12.0, "shapes[0].x1": 4.0})
    assert km == (4.0, 12.0)


def test_extract_km_from_box_selection():
    event = {
        "selection": {
            "points": [],
            "point_indices": [],
            "box": [{"x0": 10.0, "x1": 20.0, "y0": 0, "y1": 300}],
            "lasso": [],
        }
    }
    km = extract_km_range_from_plotly_selection(event)
    assert km == (10.0, 20.0)


def test_extract_indices_from_points():
    df = _sample_df()
    event = {
        "selection": {
            "points": [{"x": 3.0, "y": 200}, {"x": 7.0, "y": 210}],
            "point_indices": [30, 70],
            "box": [],
            "lasso": [],
        }
    }
    idx = extract_indices_from_plotly_selection(df, event)
    assert idx == (30, 70)


def test_build_analysis_distance_m_stitches_non_contiguous_segments():
    seg1 = pd.DataFrame({"distance_m": [5000.0, 5500.0, 6000.0], "segment_id": [0, 0, 0]})
    seg2 = pd.DataFrame({"distance_m": [25000.0, 25500.0, 26000.0], "segment_id": [1, 1, 1]})
    df = pd.concat([seg1, seg2], ignore_index=True)

    analysis = build_analysis_distance_m(df)

    assert analysis.iloc[0] == 0.0
    assert analysis.iloc[-1] == 2000.0
    assert analysis.iloc[1] == 500.0
    assert analysis.iloc[2] == 1000.0
    assert analysis.iloc[3] == 1000.0
    assert analysis.iloc[4] == 1500.0
    assert analysis.iloc[5] == 2000.0


def test_analysis_segment_boundaries_km():
    seg1 = pd.DataFrame({"distance_m": [5000.0, 6000.0], "segment_id": [0, 0]})
    seg2 = pd.DataFrame({"distance_m": [25000.0, 26000.0], "segment_id": [1, 1]})
    df = pd.concat([seg1, seg2], ignore_index=True)

    boundaries = analysis_segment_boundaries_km(df)
    assert boundaries == [1.0]


def test_build_analysis_distance_m_single_segment():
    df = _sample_df(11)
    analysis = build_analysis_distance_m(df)
    assert analysis.iloc[0] == 0.0
    assert analysis.iloc[-1] == 1000.0
