from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.app_dirs import DATA_DIR, OUTPUT_DIR


DAILY_LISTADOS_DIR = DATA_DIR / "daily_listados"
DAILY_OUTPUT_DIR = OUTPUT_DIR / "cierres_listados"


def _date_key(dt: datetime | None = None) -> str:
    current = dt or datetime.now()
    return current.strftime("%Y-%m-%d")


def _daily_dir(date_key: str | None = None) -> Path:
    path = DAILY_LISTADOS_DIR / (date_key or _date_key())
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manifest_path(date_key: str | None = None) -> Path:
    return _daily_dir(date_key) / "manifest.json"


def _load_manifest(date_key: str | None = None) -> dict[str, Any]:
    manifest_path = _manifest_path(date_key)
    if not manifest_path.exists():
        return {"entries": []}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return data
    except Exception:
        pass
    return {"entries": []}


def _save_manifest(data: dict[str, Any], date_key: str | None = None) -> None:
    manifest_path = _manifest_path(date_key)
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_signature(df: pd.DataFrame) -> str:
    normalized = df.fillna("").astype(str)
    payload = normalized.to_json(orient="split", force_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def archive_printed_listado(df: pd.DataFrame, source_name: str | None = None, printed_at: datetime | None = None) -> Path | None:
    if df is None or df.empty:
        return None

    when = printed_at or datetime.now()
    date_key = _date_key(when)
    day_dir = _daily_dir(date_key)
    manifest = _load_manifest(date_key)
    signature = _build_signature(df)

    for entry in manifest.get("entries", []):
        if entry.get("signature") == signature:
            existing = day_dir / str(entry.get("file", ""))
            if existing.exists():
                return existing

    timestamp = when.strftime("%H%M%S")
    base_name = f"listado_{timestamp}_{len(manifest['entries']) + 1:02d}.xlsx"
    out_path = day_dir / base_name
    df.reset_index(drop=True).to_excel(out_path, index=False, engine="openpyxl")

    manifest["entries"].append(
        {
            "file": base_name,
            "signature": signature,
            "source_name": (source_name or "").strip(),
            "printed_at": when.isoformat(timespec="seconds"),
            "rows": int(len(df)),
        }
    )
    _save_manifest(manifest, date_key)
    return out_path


def list_daily_archives(date_key: str | None = None) -> list[dict[str, Any]]:
    manifest = _load_manifest(date_key)
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def load_daily_listados_dataframe(date_key: str | None = None) -> pd.DataFrame:
    day_dir = _daily_dir(date_key)
    frames: list[pd.DataFrame] = []
    for entry in list_daily_archives(date_key):
        file_name = str(entry.get("file", "")).strip()
        if not file_name:
            continue
        excel_path = day_dir / file_name
        if not excel_path.exists():
            continue
        try:
            frame = pd.read_excel(excel_path, dtype=object)
        except Exception:
            continue
        if frame is None or frame.empty:
            continue
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def export_daily_listados(date_key: str | None = None) -> Path | None:
    df = load_daily_listados_dataframe(date_key)
    if df.empty:
        return None

    DAILY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    key = date_key or _date_key()
    out_path = DAILY_OUTPUT_DIR / f"fin_dia_listados_{key}.xlsx"
    df.to_excel(out_path, index=False, engine="openpyxl")
    return out_path
