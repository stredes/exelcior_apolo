from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional

GITHUB_REPO = "stredes/exelcior_apolo"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SETUP_ASSET_PATTERN = re.compile(r"ExelciorApolo_.*_Setup\.exe$", re.IGNORECASE)
PORTABLE_ZIP_ASSET_PATTERN = re.compile(r"ExelciorApolo_.*_(Portable|portable)\.zip$", re.IGNORECASE)
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
    portable_asset = None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name and url and SETUP_ASSET_PATTERN.search(name):
            setup_asset = {"name": name, "url": url}
            break
        if name and url and PORTABLE_ZIP_ASSET_PATTERN.search(name):
            portable_asset = {"name": name, "url": url}

    selected_asset = setup_asset or portable_asset
    if not selected_asset:
        return None

    return {
        "version": version,
        "tag_name": tag_name,
        "asset_name": selected_asset["name"],
        "asset_url": selected_asset["url"],
        "asset_kind": "setup" if setup_asset else "portable_zip",
        "html_url": str(payload.get("html_url") or ""),
        "published_at": str(payload.get("published_at") or ""),
        "body": str(payload.get("body") or ""),
    }


def download_release_asset(
    asset_url: str,
    asset_name: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    requests = _get_requests()
    target_dir = Path(tempfile.gettempdir()) / "ExelciorApoloUpdates"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / asset_name

    with requests.get(asset_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        total_bytes = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        with target_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if on_progress is not None:
                        on_progress(downloaded, total_bytes)
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


def launch_portable_update(zip_path: Path) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"No se encontro el paquete portable descargado: {zip_path}")
    if not getattr(sys, "frozen", False):
        raise RuntimeError("La actualizacion portable solo esta soportada en la app empaquetada.")
    if not sys.platform.startswith("win"):
        raise RuntimeError("La actualizacion portable solo esta soportada en Windows.")

    exe_path = Path(sys.executable).resolve()
    install_dir = exe_path.parent
    temp_root = Path(tempfile.gettempdir()) / "ExelciorApoloUpdates"
    extract_dir = temp_root / f"extract_{zip_path.stem}_{uuid.uuid4().hex[:8]}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    helper_path = temp_root / "apply_portable_update.ps1"
    update_config = {
        "zip_path": str(zip_path),
        "extract_dir": str(extract_dir),
        "install_dir": str(install_dir),
        "exe_name": exe_path.name,
        "desktop_names": [
            "Exelcior Apolo.lnk",
            "ExelciorApolo.lnk",
        ],
    }
    config_path = temp_root / f"portable_update_{uuid.uuid4().hex}.json"
    config_path.write_text(json.dumps(update_config, ensure_ascii=False, indent=2), encoding="utf-8")

    helper_script = r"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

config_path = Path(sys.argv[1])
cfg = json.loads(config_path.read_text(encoding="utf-8"))
zip_path = Path(cfg["zip_path"])
extract_dir = Path(cfg["extract_dir"])
install_dir = Path(cfg["install_dir"])
exe_name = cfg["exe_name"]
desktop_names = cfg.get("desktop_names", [])

time.sleep(2)
if extract_dir.exists():
    shutil.rmtree(extract_dir, ignore_errors=True)
extract_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(extract_dir)

package_dir = extract_dir / "ExelciorApolo"
if not package_dir.exists():
    dirs = [p for p in extract_dir.iterdir() if p.is_dir()]
    if len(dirs) == 1:
        package_dir = dirs[0]
if not package_dir.exists():
    raise RuntimeError("No se encontro la carpeta ExelciorApolo dentro del paquete portable.")

new_exe = package_dir / exe_name
if not new_exe.exists():
    raise RuntimeError(f"No se encontro el ejecutable esperado en el paquete: {new_exe}")

backup_dir = install_dir.parent / f"{install_dir.name}_backup"
staging_dir = install_dir.parent / f"{install_dir.name}_staging"
if backup_dir.exists():
    shutil.rmtree(backup_dir, ignore_errors=True)
if staging_dir.exists():
    shutil.rmtree(staging_dir, ignore_errors=True)

shutil.copytree(package_dir, staging_dir)
if not (staging_dir / exe_name).exists():
    raise RuntimeError("El paquete staged no contiene el ejecutable principal.")

if install_dir.exists():
    install_dir.rename(backup_dir)
staging_dir.rename(install_dir)
shutil.rmtree(backup_dir, ignore_errors=True)

desktop_dir = Path.home() / "Desktop"
target_exe = install_dir / exe_name
if desktop_dir.exists():
    for shortcut_name in desktop_names:
        shortcut_path = desktop_dir / shortcut_name
        if shortcut_path.exists():
            shortcut_path.unlink(missing_ok=True)
    ps_script = (
        "$WshShell = New-Object -ComObject WScript.Shell;"
        f"$Shortcut = $WshShell.CreateShortcut('{str((desktop_dir / desktop_names[0]).resolve()).replace(\"'\", \"''\")}');"
        f"$Shortcut.TargetPath = '{str(target_exe).replace(\"'\", \"''\")}';"
        f"$Shortcut.WorkingDirectory = '{str(install_dir).replace(\"'\", \"''\")}';"
        f"$Shortcut.IconLocation = '{str(target_exe).replace(\"'\", \"''\")},0';"
        "$Shortcut.Save();"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        check=False,
        creationflags=0x08000000,
    )

subprocess.Popen([str(target_exe)], cwd=str(install_dir))
"""
    helper_path.write_text(helper_script.strip(), encoding="utf-8")
    subprocess.Popen(
        [
            sys.executable,
            str(helper_path),
            str(config_path),
        ],
        close_fds=True,
    )


def start_update_download(
    release_info: Dict[str, str],
    on_ready,
    on_error,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> threading.Thread:
    def worker() -> None:
        try:
            asset_path = download_release_asset(
                asset_url=release_info["asset_url"],
                asset_name=release_info["asset_name"],
                on_progress=on_progress,
            )
            on_ready(asset_path)
        except Exception as exc:
            logging.exception("Fallo la descarga del instalador")
            on_error(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def release_info_to_json(release_info: Dict[str, str]) -> str:
    return json.dumps(release_info, ensure_ascii=False, indent=2)
