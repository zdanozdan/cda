"""Persist uploaded ride files across browser reloads."""

from __future__ import annotations

import json
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / ".cda_calc_uploads"
TCX_FILE = UPLOAD_DIR / "ride.tcx"
TCX_META = UPLOAD_DIR / "ride.tcx.json"
SPLITS_FILE = UPLOAD_DIR / "splits.csv"
SPLITS_META = UPLOAD_DIR / "splits.csv.json"


def _ensure_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _write_meta(path: Path, name: str) -> None:
    path.write_text(json.dumps({"name": name}, ensure_ascii=False), encoding="utf-8")


def _read_meta(path: Path, default: str) -> str:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("name", default)
    except (json.JSONDecodeError, OSError):
        return default


def save_tcx(data: bytes, name: str) -> None:
    _ensure_dir()
    TCX_FILE.write_bytes(data)
    _write_meta(TCX_META, name)


def load_tcx() -> tuple[bytes, str] | None:
    if not TCX_FILE.exists():
        return None
    return TCX_FILE.read_bytes(), _read_meta(TCX_META, TCX_FILE.name)


def clear_tcx() -> None:
    for path in (TCX_FILE, TCX_META):
        if path.exists():
            path.unlink()


def save_splits(data: bytes, name: str) -> None:
    _ensure_dir()
    SPLITS_FILE.write_bytes(data)
    _write_meta(SPLITS_META, name)


def load_splits() -> tuple[bytes, str] | None:
    if not SPLITS_FILE.exists():
        return None
    return SPLITS_FILE.read_bytes(), _read_meta(SPLITS_META, SPLITS_FILE.name)


def clear_splits() -> None:
    for path in (SPLITS_FILE, SPLITS_META):
        if path.exists():
            path.unlink()
