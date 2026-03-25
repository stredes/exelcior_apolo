from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional

GITHUB_REPO = "stredes/exelcior_apolo"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SETUP_ASSET_PATTERN = re.compile(r"ExelciorApolo_.*_Setup\.exe$", re.IGNORECASE)
REQUEST_TIMEOUT = 12


def _get_requests():
    try:
        import requests  # type: ignore

        return requests
    except Exception as exc:
        raise RuntimeError(
            "La dependencia 'requests' no está instalada. Ejecuta pip install requests."
        ) from exc


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def get_local_version() -> str:
    candidates = [
        _resource_root() / "assets" / "version" / "exelcior_apolo_version.txt",
        Path(__file__).resolve().parent.parent / "assets" / "version" / "exelcior_apolo_version.txt",
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"StringStruct\('FileVersion','(\d+\.\d+\.\d+)'\)", content)
            if match:
                return match.group(1)
        except Exception:
            logging.exception("No se pudo leer la version local desde %s", path)
    return "0.0.0"


def _version_key(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version or "")
    return tuple(int(part) for part in parts[:4]) or (0, 0, 0)


def is_newer_version(latest: str, current: str) -> bool:
    return _version_key(latest) > _version_key(current)


def fetch_latest_release() -> Optional[Dict[str, Any]]:
    requests = _get_requests()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ExelciorApoloUpdater/1.0",
    }
    response = requests.get(GITHUB_API_LATEST, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("GitHub API devolvio una respuesta invalida.")
    return payload


def parse_release_info(payload: Dict[str, Any]) -> Optional[Dict[str, str]]:
    tag_name = str(payload.get("tag_name") or "").strip()
    version = tag_name.lstrip("vV")
    if not version:
        return None

    assets = payload.get("assets") or []
    setup_asset = None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name and url and SETUP_ASSET_PATTERN.search(name):
            setup_asset = {"name": name, "url": url}
            break

    if not setup_asset:
        return None

    return {
        "version": version,
        "tag_name": tag_name,
        "asset_name": setup_asset["name"],
        "asset_url": setup_asset["url"],
        "html_url": str(payload.get("html_url") or ""),
        "published_at": str(payload.get("published_at") or ""),
        "body": str(payload.get("body") or ""),
    }


def download_installer(asset_url: str, asset_name: str) -> Path:
    requests = _get_requests()
    target_dir = Path(tempfile.gettempdir()) / "ExelciorApoloUpdates"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / asset_name

    with requests.get(asset_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with target_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fh.write(chunk)
    return target_path


def launch_installer(installer_path: Path) -> None:
    if not installer_path.exists():
        raise FileNotFoundError(f"No se encontro el instalador descargado: {installer_path}")

    if sys.platform.startswith("win"):
        subprocess.Popen(
            [str(installer_path), "/SP-", "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS"],
            close_fds=True,
        )
        return

    raise RuntimeError("La instalacion automatica solo esta soportada en Windows.")


def start_update_download(
    release_info: Dict[str, str],
    on_ready,
    on_error,
) -> threading.Thread:
    def worker() -> None:
        try:
            installer_path = download_installer(
                asset_url=release_info["asset_url"],
                asset_name=release_info["asset_name"],
            )
            on_ready(installer_path)
        except Exception as exc:
            logging.exception("Fallo la descarga del instalador")
            on_error(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def release_info_to_json(release_info: Dict[str, str]) -> str:
    return json.dumps(release_info, ensure_ascii=False, indent=2)
