from __future__ import annotations

import shutil
import os
import sys
from pathlib import Path
from typing import Iterable

try:
    from platformdirs import user_data_dir
except Exception:
    def user_data_dir(appname: str, appauthor: str | None = None) -> str:
        home = Path.home()
        if sys.platform.startswith("win"):
            base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or home / "AppData" / "Local")
        elif sys.platform == "darwin":
            base = home / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")

        if appauthor:
            return str(base / appauthor / appname)
        return str(base / appname)

APP_NAME = "ExelciorApolo"
APP_AUTHOR = "stredes"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
CONFIG_DIR = APP_DATA_DIR / "config"
DATA_DIR = APP_DATA_DIR / "data"
LOGS_DIR = APP_DATA_DIR / "logs"
OUTPUT_DIR = APP_DATA_DIR / "output"


def ensure_app_dirs() -> None:
    for path in (APP_DATA_DIR, CONFIG_DIR, DATA_DIR, LOGS_DIR, OUTPUT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _normalize_candidates(paths: Iterable[Path | str]) -> list[Path]:
    candidates: list[Path] = []
    for path in paths:
        candidate = path if isinstance(path, Path) else Path(path)
        candidates.append(candidate)
    return candidates


def migrate_file(target: Path, legacy_candidates: Iterable[Path | str] = ()) -> Path:
    ensure_app_dirs()
    if target.exists():
        return target

    for legacy in _normalize_candidates(legacy_candidates):
        if not legacy.exists() or not legacy.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
        return target

    return target


def ensure_file(
    target: Path,
    legacy_candidates: Iterable[Path | str] = (),
    default_text: str | None = None,
) -> Path:
    target = migrate_file(target, legacy_candidates=legacy_candidates)
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    if default_text is not None:
        target.write_text(default_text, encoding="utf-8")
    return target
