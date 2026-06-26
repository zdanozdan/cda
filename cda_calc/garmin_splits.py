"""Parser for Garmin lap-split CSV exports (PL / EN)."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

_SUMMARY_LABELS = {"podsumowanie", "summary", "total", "razem"}


@dataclass(frozen=True)
class GarminLap:
    number: int
    distance_km: float
    duration_s: float
    cumulative_time_s: float
    avg_speed_kph: float | None
    avg_power_w: float | None
    avg_temp_c: float | None
    km_start: float
    km_end: float


def _normalize_header(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _pick_column(columns: list[str], *candidates: str) -> str | None:
    normalized = {_normalize_header(c): c for c in columns}
    for candidate in candidates:
        key = _normalize_header(candidate)
        if key in normalized:
            return normalized[key]
    return None


def parse_duration_to_seconds(text: str) -> float:
    """Parse Garmin duration strings: ``7:55.3``, ``1:04:11``, ``12:47``."""
    raw = text.strip()
    if not raw or raw == "--":
        return 0.0

    if "." in raw and raw.count(":") == 1:
        minutes, seconds = raw.split(":", 1)
        return int(minutes) * 60 + float(seconds)

    parts = raw.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    raise ValueError(f"Nieznany format czasu: {text!r}")


def _parse_float(text: str) -> float | None:
    raw = text.strip().replace(",", "")
    if not raw or raw == "--":
        return None
    return float(raw)


def parse_garmin_splits_csv(source: str | Path | BinaryIO | bytes) -> list[GarminLap]:
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    elif isinstance(source, bytes):
        raw = source
    else:
        raw = source.read()

    for encoding in ("utf-8-sig", "utf-8", "cp1250", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Nie udało się odczytać pliku CSV (kodowanie).")

    table = pd.read_csv(io.StringIO(text))
    if table.empty:
        raise ValueError("Plik CSV podziałów jest pusty.")

    columns = [str(c) for c in table.columns]
    lap_col = _pick_column(columns, "Okrążenia", "Lap", "Split", "Okrązenie")
    dist_col = _pick_column(columns, "Dystans", "Distance")
    time_col = _pick_column(columns, "Czas", "Time", "Lap Time")
    cum_time_col = _pick_column(columns, "Łączny czas", "Elapsed Time", "Moving Time")
    speed_col = _pick_column(columns, "Średnia prędkość", "Avg Speed", "Average Speed")
    power_col = _pick_column(columns, "Średnia moc", "Avg Power", "Average Power")
    temp_col = _pick_column(
        columns,
        "Średnia temperatura",
        "Avg Temperature",
        "Average Temperature",
        "Temperature",
    )

    if lap_col is None or dist_col is None:
        raise ValueError("CSV nie wygląda na eksport podziałów Garmin (brak kolumn okrążeń / dystansu).")

    laps: list[GarminLap] = []
    cumulative_km = 0.0

    for _, row in table.iterrows():
        label = str(row[lap_col]).strip()
        if _normalize_header(label) in _SUMMARY_LABELS:
            continue
        if not label.isdigit():
            continue

        distance_km = _parse_float(str(row[dist_col]))
        if distance_km is None or distance_km <= 0:
            continue

        duration_s = parse_duration_to_seconds(str(row[time_col])) if time_col else 0.0
        cumulative_time_s = (
            parse_duration_to_seconds(str(row[cum_time_col])) if cum_time_col else duration_s
        )
        avg_speed_kph = _parse_float(str(row[speed_col])) if speed_col else None
        avg_power_w = _parse_float(str(row[power_col])) if power_col else None
        avg_temp_c = _parse_float(str(row[temp_col])) if temp_col else None

        km_start = cumulative_km
        cumulative_km += distance_km
        laps.append(
            GarminLap(
                number=int(label),
                distance_km=distance_km,
                duration_s=duration_s,
                cumulative_time_s=cumulative_time_s,
                avg_speed_kph=avg_speed_kph,
                avg_power_w=avg_power_w,
                avg_temp_c=avg_temp_c,
                km_start=km_start,
                km_end=cumulative_km,
            )
        )

    if not laps:
        raise ValueError("Nie znaleziono okrążeń w pliku CSV.")

    return laps


def align_laps_to_ride(laps: list[GarminLap], ride_total_km: float) -> list[GarminLap]:
    """Scale lap km ranges when CSV total distance differs slightly from TCX."""
    csv_total = laps[-1].km_end
    if csv_total <= 0 or ride_total_km <= 0:
        return laps
    ratio = ride_total_km / csv_total
    if abs(ratio - 1.0) < 0.02:
        return laps

    scaled: list[GarminLap] = []
    for lap in laps:
        scaled.append(
            GarminLap(
                number=lap.number,
                distance_km=lap.distance_km * ratio,
                duration_s=lap.duration_s,
                cumulative_time_s=lap.cumulative_time_s,
                avg_speed_kph=lap.avg_speed_kph,
                avg_power_w=lap.avg_power_w,
                avg_temp_c=lap.avg_temp_c,
                km_start=lap.km_start * ratio,
                km_end=lap.km_end * ratio,
            )
        )
    return scaled


def average_temperature_c(laps: list[GarminLap], lap_numbers: list[int] | None = None) -> float | None:
    """Duration-weighted mean temperature from Garmin lap splits."""
    pool = laps if lap_numbers is None else [lap for lap in laps if lap.number in lap_numbers]
    weighted: list[tuple[float, float]] = []
    for lap in pool:
        if lap.avg_temp_c is None:
            continue
        weight = lap.duration_s if lap.duration_s > 0 else lap.distance_km
        if weight <= 0:
            continue
        weighted.append((lap.avg_temp_c, weight))
    if not weighted:
        return None
    total_weight = sum(weight for _, weight in weighted)
    return sum(temp * weight for temp, weight in weighted) / total_weight


def lap_label(lap: GarminLap, *, lap_word: str = "Okr.") -> str:
    power = f"{lap.avg_power_w:.0f} W" if lap.avg_power_w is not None else "—"
    speed = f"{lap.avg_speed_kph:.1f} km/h" if lap.avg_speed_kph is not None else "—"
    return (
        f"{lap_word} {lap.number}: {lap.km_start:.2f}–{lap.km_end:.2f} km · "
        f"{lap.distance_km:.2f} km · {power} · {speed}"
    )


def selected_lap_ranges(laps: list[GarminLap], selected_numbers: list[int]) -> list[tuple[float, float]]:
    selected = {n for n in selected_numbers}
    return [(lap.km_start, lap.km_end) for lap in laps if lap.number in selected]
