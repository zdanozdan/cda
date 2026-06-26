from pathlib import Path

import pytest

from cda_calc.tcx_parser import find_turnaround_index, parse_tcx

FIXTURE = Path(__file__).parent / "fixtures" / "sample_ride.tcx"
GARMIN_DISTANCE_FIXTURE = Path(__file__).parent / "fixtures" / "garmin_distance.tcx"
USER_LONG_RIDE = Path("/Users/zdanozdan/Downloads/activity_1197294680.tcx")


def test_parse_sample_tcx():
    ride = parse_tcx(FIXTURE)
    assert len(ride.df) == 3
    assert ride.has_power
    assert ride.speed_source == "sensor"
    assert ride.df["power_w"].notna().all()
    assert ride.df["speed_mps"].notna().all()
    assert ride.laps


def test_parse_missing_power_raises():
    xml = FIXTURE.read_text().replace("<ns3:Watts>250</ns3:Watts>", "")
    xml = xml.replace("<ns3:Watts>255</ns3:Watts>", "")
    xml = xml.replace("<ns3:Watts>252</ns3:Watts>", "")
    with pytest.raises(ValueError, match="mocy"):
        parse_tcx(xml.encode())


def test_find_turnaround_index():
    from tests.synthetic import make_out_and_back_ride

    df = make_out_and_back_ride(n_out=50, n_back=50)
    idx = find_turnaround_index(df)
    assert 45 <= idx <= 55


def test_parse_uses_garmin_distance_meters():
    from cda_calc.segment import total_distance_km

    ride = parse_tcx(GARMIN_DISTANCE_FIXTURE)
    assert ride.df["distance_m"].notna().all()
    assert total_distance_km(ride.df) == pytest.approx(0.03, abs=0.001)


@pytest.mark.skipif(not USER_LONG_RIDE.exists(), reason="local regression file")
def test_parse_long_garmin_ride_distance():
    from cda_calc.segment import total_distance_km

    ride = parse_tcx(USER_LONG_RIDE)
    total_km = total_distance_km(ride.df)
    assert 85.0 <= total_km <= 86.5
    assert ride.df["distance_m"].notna().all()
    duration_min = (
        ride.df["timestamp"].iloc[-1] - ride.df["timestamp"].iloc[0]
    ).total_seconds() / 60
    assert duration_min > 120


def test_distance_integrates_through_missing_gps(tmp_path):
    from cda_calc.segment import total_distance_km

    xml = FIXTURE.read_text()
    # Drop middle position so haversine chain must use speed fallback.
    xml = xml.replace(
        """          <Trackpoint>
            <Time>2024-06-01T08:00:01Z</Time>
            <Position>
              <LatitudeDegrees>52.1001</LatitudeDegrees>
              <LongitudeDegrees>21.0001</LongitudeDegrees>
            </Position>
            <AltitudeMeters>100.5</AltitudeMeters>
            <Extensions>
              <ns3:TPX>
                <ns3:Speed>10.2</ns3:Speed>
                <ns3:Watts>255</ns3:Watts>
              </ns3:TPX>
            </Extensions>
          </Trackpoint>""",
        """          <Trackpoint>
            <Time>2024-06-01T08:00:01Z</Time>
            <AltitudeMeters>100.5</AltitudeMeters>
            <Extensions>
              <ns3:TPX>
                <ns3:Speed>10.2</ns3:Speed>
                <ns3:Watts>255</ns3:Watts>
              </ns3:TPX>
            </Extensions>
          </Trackpoint>""",
    )
    path = tmp_path / "gap.tcx"
    path.write_text(xml)
    ride = parse_tcx(path)
    assert ride.df["distance_m"].notna().all()
    assert total_distance_km(ride.df) > 0
