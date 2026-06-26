from __future__ import annotations

import math
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd
from lxml import etree

from cda_calc.models import RideData

TCX_NS = {
    "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ext": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
}


def _parse_time(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _text(el: etree._Element | None, path: str, ns: dict) -> str | None:
    if el is None:
        return None
    found = el.find(path, namespaces=ns)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def _float(el: etree._Element | None, path: str, ns: dict) -> float | None:
    text = _text(el, path, ns)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _extract_laps(root: etree._Element) -> list[dict]:
    laps = []
    for lap in root.findall(".//tcx:Lap", namespaces=TCX_NS):
        start = _parse_time(_text(lap, "tcx:StartTime", TCX_NS))
        laps.append(
            {
                "start_time": start,
                "total_time_s": _float(lap, "tcx:TotalTimeSeconds", TCX_NS),
                "distance_m": _float(lap, "tcx:DistanceMeters", TCX_NS),
            }
        )
    return laps


def _integrate_distance_haversine(df: pd.DataFrame) -> pd.Series:
    """Cumulative distance from GPS positions, with speed×Δt fallback."""
    distance = np.zeros(len(df), dtype=float)
    for i in range(1, len(df)):
        lat1, lon1 = df.at[i - 1, "latitude"], df.at[i - 1, "longitude"]
        lat2, lon2 = df.at[i, "latitude"], df.at[i, "longitude"]
        if None not in (lat1, lon1, lat2, lon2) and not (pd.isna(lat1) or pd.isna(lat2)):
            step = _haversine_m(lat1, lon1, lat2, lon2)
        else:
            dt = (df.at[i, "timestamp"] - df.at[i - 1, "timestamp"]).total_seconds()
            speed = df.at[i, "speed_mps"]
            if speed is None or pd.isna(speed):
                speed = df.at[i - 1, "speed_mps"]
            if speed is None or pd.isna(speed):
                speed = 0.0
            step = float(speed) * max(dt, 0)
        distance[i] = distance[i - 1] + step
    return pd.Series(distance, index=df.index)


def _distance_from_tcx_field(df: pd.DataFrame) -> pd.Series | None:
    """Use Garmin cumulative DistanceMeters when present on most trackpoints."""
    tcx = pd.to_numeric(df.get("tcx_distance_m"), errors="coerce")
    if tcx is None or tcx.notna().sum() < len(df) * 0.5:
        return None
    origin = float(tcx.dropna().iloc[0])
    dist = tcx - origin
    return dist.interpolate(method="linear", limit_direction="both")


def _build_distance_m(df: pd.DataFrame) -> pd.Series:
    tcx_dist = _distance_from_tcx_field(df)
    if tcx_dist is not None:
        return tcx_dist
    return _integrate_distance_haversine(df)


def parse_tcx(source: str | Path | BinaryIO | bytes) -> RideData:
    if isinstance(source, (str, Path)):
        tree = etree.parse(str(source))
        filename = Path(source).name
    elif isinstance(source, bytes):
        tree = etree.parse(BytesIO(source))
        filename = ""
    else:
        tree = etree.parse(source)
        filename = getattr(source, "name", "") or ""

    root = tree.getroot()
    rows: list[dict] = []
    sensor_speed_count = 0
    gps_speed_count = 0

    for tp in root.findall(".//tcx:Trackpoint", namespaces=TCX_NS):
        ts = _parse_time(_text(tp, "tcx:Time", TCX_NS))
        if ts is None:
            continue

        lat = _float(tp, "tcx:Position/tcx:LatitudeDegrees", TCX_NS)
        lon = _float(tp, "tcx:Position/tcx:LongitudeDegrees", TCX_NS)
        altitude = _float(tp, "tcx:AltitudeMeters", TCX_NS)
        hr = _float(tp, "tcx:HeartRateBpm/tcx:Value", TCX_NS)
        tcx_distance_m = _float(tp, "tcx:DistanceMeters", TCX_NS)

        tpx = tp.find("tcx:Extensions/ext:TPX", namespaces=TCX_NS)
        speed = _float(tpx, "ext:Speed", TCX_NS) if tpx is not None else None
        power = _float(tpx, "ext:Watts", TCX_NS) if tpx is not None else None
        cadence = _float(tpx, "ext:RunCadence", TCX_NS) if tpx is not None else None
        if cadence is None and tpx is not None:
            cadence = _float(tpx, "ext:Cadence", TCX_NS)

        rows.append(
            {
                "timestamp": ts,
                "latitude": lat,
                "longitude": lon,
                "elevation_m": altitude,
                "tcx_distance_m": tcx_distance_m,
                "power_w": power,
                "speed_mps": speed,
                "cadence": cadence,
                "heart_rate": hr,
            }
        )
        if speed is not None:
            sensor_speed_count += 1

    if not rows:
        raise ValueError("Plik TCX nie zawiera punktów trasy (Trackpoint).")

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)

    # GPS speed fallback
    gps_speed = np.full(len(df), np.nan)
    for i in range(1, len(df)):
        lat1, lon1 = df.at[i - 1, "latitude"], df.at[i - 1, "longitude"]
        lat2, lon2 = df.at[i, "latitude"], df.at[i, "longitude"]
        if None in (lat1, lon1, lat2, lon2) or pd.isna(lat1):
            continue
        dt = (df.at[i, "timestamp"] - df.at[i - 1, "timestamp"]).total_seconds()
        if dt <= 0:
            continue
        dist = _haversine_m(lat1, lon1, lat2, lon2)
        gps_speed[i] = dist / dt

    missing_speed = df["speed_mps"].isna()
    df.loc[missing_speed, "speed_mps"] = gps_speed[missing_speed]
    gps_speed_count = int(missing_speed.sum())

    if df["speed_mps"].isna().all():
        raise ValueError("Brak danych prędkości (ani czujnik, ani GPS).")

    has_power = df["power_w"].notna().any()
    if not has_power:
        raise ValueError("Brak danych mocy (Watts) — wymagany power meter.")

    if sensor_speed_count == 0:
        speed_source = "gps"
    elif gps_speed_count == 0:
        speed_source = "sensor"
    else:
        speed_source = "mixed"

    # Cumulative distance — prefer Garmin DistanceMeters from TCX trackpoints.
    df["distance_m"] = _build_distance_m(df)

    laps = _extract_laps(root)
    return RideData(df=df, speed_source=speed_source, has_power=has_power, laps=laps, filename=filename)


def slice_ride(df: pd.DataFrame, start_idx: int, end_idx: int) -> pd.DataFrame:
    segment = df.iloc[start_idx : end_idx + 1].copy().reset_index(drop=True)
    if segment.empty:
        raise ValueError("Wybrany segment jest pusty.")
    return segment


def find_turnaround_index(df: pd.DataFrame) -> int:
    """Index of farthest point from start — typical out-and-back turnaround."""
    if df.empty:
        return 0
    start_lat = df.at[0, "latitude"]
    start_lon = df.at[0, "longitude"]
    if start_lat is None or pd.isna(start_lat):
        return len(df) // 2

    max_dist = -1.0
    max_idx = 0
    for i in range(len(df)):
        lat, lon = df.at[i, "latitude"], df.at[i, "longitude"]
        if lat is None or pd.isna(lat):
            continue
        d = _haversine_m(start_lat, start_lon, lat, lon)
        if d > max_dist:
            max_dist = d
            max_idx = i
    return max_idx
