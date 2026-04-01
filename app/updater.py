from __future__ import annotations

import json
import logging
import os
import re
import hashlib
import ctypes
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

GITHUB_REPO = "stredes/exelcior_apolo"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SETUP_ASSET_PATTERN = re.compile(r"ExelciorApolo_.*_Setup\.exe$", re.IGNORECASE)
PORTABLE_ZIP_ASSET_PATTERN = re.compile(r"ExelciorApolo_.*_(Portable|portable)\.zip$", re.IGNORECASE)
CHECKSUM_ASSET_PATTERN = re.compile(r"checksums_.*\.txt$", re.IGNORECASE)
REQUEST_TIMEOUT = 12
UPDATE_RUNTIME_DIRNAME = "ExelciorApoloUpdates"
UPDATE_STATE_FILE = "portable_update_state.json"
UPDATE_LOG_FILE = "portable_update_last.log"
PORTABLE_APP_DIRNAME = "ExelciorApolo"


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


def _get_runtime_exe_path() -> Path:
    return Path(sys.executable).resolve() if getattr(sys, "frozen", False) else Path(__file__).resolve()


def _is_program_files_path(path: Path) -> bool:
    text = str(path).lower()
    candidates = [
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
    ]
    return any(candidate and text.startswith(str(Path(candidate)).lower()) for candidate in candidates)


def should_prefer_portable_asset() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    exe_path = _get_runtime_exe_path()
    install_dir = exe_path.parent
    if install_dir.name.lower() != PORTABLE_APP_DIRNAME.lower():
        return False
    if _is_program_files_path(install_dir):
        return False
    return True


def is_installed_in_program_files() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    exe_path = _get_runtime_exe_path()
    return _is_program_files_path(exe_path.parent)


def _windows_quote_arg(value: str) -> str:
    text = str(value or "")
    if not text:
        return '""'
    if not any(ch in text for ch in ' \t"'):
        return text
    return '"' + text.replace('"', '\\"') + '"'


def _launch_windows_installer_elevated(installer_path: Path, args: list[str]) -> None:
    parameters = " ".join(_windows_quote_arg(arg) for arg in args)
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        str(installer_path),
        parameters,
        str(installer_path.parent),
        1,
    )
    if result <= 32:
        error_map = {
            2: "No se encontro el archivo del instalador.",
            3: "No se encontro la ruta del instalador.",
            5: "Windows denego el acceso al instalador.",
            27: "La asociacion del archivo no es valida.",
            31: "No hay una aplicacion asociada para ejecutar el instalador.",
            1223: "La elevacion fue cancelada por el usuario.",
        }
        detail = error_map.get(int(result), f"Codigo de ShellExecuteW: {int(result)}")
        raise RuntimeError(
            "No se pudo iniciar la actualizacion con permisos de administrador. "
            f"{detail}"
        )


def get_update_runtime_dir() -> Path:
    path = Path(tempfile.gettempdir()) / UPDATE_RUNTIME_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_update_session_dir() -> Path:
    session_dir = get_update_runtime_dir() / f"session_{uuid.uuid4().hex}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def get_update_log_path() -> Path:
    return get_update_runtime_dir() / UPDATE_LOG_FILE


def _get_update_state_path() -> Path:
    return get_update_runtime_dir() / UPDATE_STATE_FILE


def _write_update_state(payload: Dict[str, Any]) -> Path:
    state_path = _get_update_state_path()
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return state_path


def read_update_state() -> Optional[Dict[str, Any]]:
    state_path = _get_update_state_path()
    if not state_path.exists():
        return None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        logging.exception("No se pudo leer el estado del actualizador desde %s", state_path)
    return None


def clear_update_state() -> None:
    state_path = _get_update_state_path()
    try:
        if state_path.exists():
            state_path.unlink()
    except Exception:
        logging.exception("No se pudo limpiar el estado del actualizador")


def get_update_startup_notice(current_version: str) -> Optional[Dict[str, str]]:
    state = read_update_state()
    if not state:
        return None

    status = str(state.get("status") or "").strip().lower()
    target_version = str(state.get("target_version") or "").strip()
    log_path = str(state.get("log_path") or get_update_log_path())
    error_message = str(state.get("error") or "").strip()

    if status == "applied" and target_version and current_version == target_version:
        clear_update_state()
        return {
            "level": "info",
            "message": f"Actualizacion aplicada correctamente a la version {target_version}.",
        }

    if status == "failed":
        clear_update_state()
        extra = f"\nRevisa el log: {log_path}" if log_path else ""
        return {
            "level": "warning",
            "message": f"No se pudo completar la actualizacion automatica.{extra}" + (f"\nDetalle: {error_message}" if error_message else ""),
        }

    if status in {"pending", "applied"} and target_version and current_version != target_version:
        clear_update_state()
        extra = f"\nRevisa el log: {log_path}" if log_path else ""
        return {
            "level": "warning",
            "message": (
                f"La actualizacion esperaba dejar la version {target_version}, "
                f"pero la app inicio en {current_version}.{extra}"
            ),
        }

    clear_update_state()
    return None


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


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            if chunk:
                digest.update(chunk)
    return digest.hexdigest()


def _download_text_asset(asset_url: str) -> str:
    requests = _get_requests()
    with requests.get(asset_url, timeout=REQUEST_TIMEOUT) as response:
        response.raise_for_status()
        return response.text


def _parse_checksums(content: str) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.search(r"([A-Fa-f0-9]{64})\s+\*(.+)$", line)
        if not match:
            continue
        hashes[Path(match.group(2).strip()).name] = match.group(1).lower()
    return hashes


def _verify_windows_signature(path: Path) -> None:
    if not sys.platform.startswith("win"):
        return
    if path.suffix.lower() != ".exe":
        return

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$sig = Get-AuthenticodeSignature -LiteralPath $args[0]; "
            "if ($sig.Status -ne 'Valid') { "
            "Write-Output ($sig.Status.ToString()); exit 1 "
            "} "
            "Write-Output ($sig.SignerCertificate.Subject)"
        ),
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stdout or result.stderr or "firma no valida").strip()
        raise RuntimeError(
            f"La firma digital del instalador no es valida para {path.name}: {detail}"
        )


def verify_downloaded_asset(asset_path: Path, release_info: Dict[str, str]) -> None:
    checksum_url = str(release_info.get("checksum_url") or "").strip()
    if not checksum_url:
        raise RuntimeError(
            "La release no publica checksums. Se cancela la actualizacion por seguridad."
        )

    checksums = _parse_checksums(_download_text_asset(checksum_url))
    expected_hash = checksums.get(asset_path.name)
    if not expected_hash:
        raise RuntimeError(
            f"No se encontro checksum publicado para {asset_path.name}. Actualizacion cancelada."
        )

    current_hash = _compute_sha256(asset_path)
    if current_hash.lower() != expected_hash.lower():
        raise RuntimeError(
            f"Checksum invalido para {asset_path.name}. Esperado {expected_hash}, obtenido {current_hash}."
        )

    if str(release_info.get("asset_kind") or "") == "setup":
        _verify_windows_signature(asset_path)


def parse_release_info(payload: Dict[str, Any]) -> Optional[Dict[str, str]]:
    tag_name = str(payload.get("tag_name") or "").strip()
    version = tag_name.lstrip("vV")
    if not version:
        return None

    assets = payload.get("assets") or []
    setup_asset = None
    portable_asset = None
    checksum_asset = None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name and url and CHECKSUM_ASSET_PATTERN.search(name):
            checksum_asset = {"name": name, "url": url}
        elif name and url and SETUP_ASSET_PATTERN.search(name):
            setup_asset = {"name": name, "url": url}
        elif name and url and PORTABLE_ZIP_ASSET_PATTERN.search(name):
            portable_asset = {"name": name, "url": url}

    prefer_portable = should_prefer_portable_asset()
    requires_setup = is_installed_in_program_files()
    if requires_setup:
        if not setup_asset:
            return {
                "version": version,
                "tag_name": tag_name,
                "asset_name": "",
                "asset_url": "",
                "asset_kind": "setup_missing",
                "checksum_name": str((checksum_asset or {}).get("name") or ""),
                "checksum_url": str((checksum_asset or {}).get("url") or ""),
                "html_url": str(payload.get("html_url") or ""),
                "published_at": str(payload.get("published_at") or ""),
                "body": str(payload.get("body") or ""),
            }
        selected_asset = setup_asset
        selected_kind = "setup"
    else:
        selected_asset = portable_asset if prefer_portable and portable_asset else (setup_asset or portable_asset)
        if not selected_asset:
            return None
        selected_kind = "portable_zip" if selected_asset == portable_asset else "setup"
    return {
        "version": version,
        "tag_name": tag_name,
        "asset_name": selected_asset["name"],
        "asset_url": selected_asset["url"],
        "asset_kind": selected_kind,
        "checksum_name": str((checksum_asset or {}).get("name") or ""),
        "checksum_url": str((checksum_asset or {}).get("url") or ""),
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
    target_dir = create_update_session_dir()
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
        args = ["/SP-", "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS"]
        if is_installed_in_program_files():
            _launch_windows_installer_elevated(installer_path, args)
        else:
            subprocess.Popen(
                [str(installer_path), *args],
                close_fds=True,
            )
        return

    raise RuntimeError("La instalacion automatica solo esta soportada en Windows.")


def launch_portable_update(zip_path: Path, target_version: str = "") -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"No se encontro el paquete portable descargado: {zip_path}")
    if not getattr(sys, "frozen", False):
        raise RuntimeError("La actualizacion portable solo esta soportada en la app empaquetada.")
    if not sys.platform.startswith("win"):
        raise RuntimeError("La actualizacion portable solo esta soportada en Windows.")

    exe_path = Path(sys.executable).resolve()
    install_dir = exe_path.parent
    if install_dir.name.lower() != PORTABLE_APP_DIRNAME.lower():
        raise RuntimeError(
            "La actualización portable solo puede aplicarse cuando la app corre desde una carpeta portable 'ExelciorApolo'."
        )
    if _is_program_files_path(install_dir):
        raise RuntimeError(
            "La app actual parece instalada en Program Files. Para ese caso se debe usar el instalador, no el parche portable."
        )
    temp_root = get_update_runtime_dir()
    session_root = create_update_session_dir()
    extract_dir = session_root / f"extract_{zip_path.stem}_{uuid.uuid4().hex[:8]}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    helper_path = session_root / "apply_portable_update.ps1"
    log_path = get_update_log_path()
    if not _is_relative_to(session_root, temp_root):
        raise RuntimeError("La sesión del actualizador quedó fuera del runtime temporal permitido.")
    if not _is_relative_to(extract_dir, session_root):
        raise RuntimeError("La carpeta de extracción quedó fuera de la sesión permitida.")
    if exe_path.name.strip() == "":
        raise RuntimeError("No se pudo resolver el ejecutable actual para la actualización portable.")
    update_config = {
        "zip_path": str(zip_path),
        "extract_dir": str(extract_dir),
        "install_dir": str(install_dir),
        "exe_name": exe_path.name,
        "current_pid": os.getpid(),
        "target_version": target_version.strip(),
        "state_path": str(_get_update_state_path()),
        "log_path": str(log_path),
        "desktop_names": [
            "Exelcior Apolo.lnk",
            "ExelciorApolo.lnk",
        ],
        "desktop_exe_names": [
            exe_path.name,
        ],
    }
    config_path = session_root / f"portable_update_{uuid.uuid4().hex}.json"
    config_path.write_text(json.dumps(update_config, ensure_ascii=False, indent=2), encoding="utf-8")
    updater_template_path = _resource_root() / "data" / "portable_updater.ps1"
    if updater_template_path.exists():
        helper_script = updater_template_path.read_text(encoding="utf-8")
    else:
        helper_script = r"""
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -LiteralPath '__CONFIG_PATH__' -Raw | ConvertFrom-Json
$zipPath = [string]$cfg.zip_path
$extractDir = [string]$cfg.extract_dir
$installDir = [string]$cfg.install_dir
$exeName = [string]$cfg.exe_name
$currentPid = [int]$cfg.current_pid
$targetVersion = [string]$cfg.target_version
$statePath = [string]$cfg.state_path
$desktopNames = @($cfg.desktop_names)
$desktopExeNames = @($cfg.desktop_exe_names)
$parentDir = Split-Path -Parent $installDir
$backupDir = Join-Path $parentDir ((Split-Path -Leaf $installDir) + '_backup')
$stagingDir = Join-Path $parentDir ((Split-Path -Leaf $installDir) + '_staging')
$logPath = '__LOG_PATH__'

function Write-Log([string]$message) {
  $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Add-Content -LiteralPath $logPath -Value "[$timestamp] $message" -Encoding UTF8
}

function Save-State([string]$status, [string]$errorMessage = '') {
  $payload = @{
    status = $status
    target_version = $targetVersion
    install_dir = $installDir
    log_path = $logPath
    error = $errorMessage
    updated_at = (Get-Date).ToString('s')
  } | ConvertTo-Json -Depth 5
  Set-Content -LiteralPath $statePath -Value $payload -Encoding UTF8
}

try {
  if (Test-Path -LiteralPath $logPath) {
    Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue
  }
  Save-State -status 'pending'

  Write-Log 'Inicio de parche portable.'
  Write-Log "ZIP: $zipPath"
  Write-Log "InstallDir: $installDir"
  Write-Log "PID actual: $currentPid"

  for ($i = 0; $i -lt 120; $i++) {
    $proc = Get-Process -Id $currentPid -ErrorAction SilentlyContinue
    if (-not $proc) {
      Write-Log 'Proceso principal liberado.'
      break
    }
    Start-Sleep -Milliseconds 500
  }

  if (Get-Process -Id $currentPid -ErrorAction SilentlyContinue) {
    throw "La aplicaci?n principal no se cerr? a tiempo. PID: $currentPid"
  }

  if (Test-Path -LiteralPath $extractDir) {
    Write-Log 'Limpiando extractDir anterior.'
    Remove-Item -LiteralPath $extractDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  if (Test-Path -LiteralPath $stagingDir) {
    Write-Log 'Limpiando stagingDir anterior.'
    Remove-Item -LiteralPath $stagingDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

  Write-Log 'Expandiendo ZIP portable.'
  Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

  $packageDir = Join-Path $extractDir 'ExelciorApolo'
  if (-not (Test-Path -LiteralPath $packageDir)) {
    $dirs = @(Get-ChildItem -LiteralPath $extractDir -Directory)
    if ($dirs.Count -eq 1) {
      $packageDir = $dirs[0].FullName
    }
  }
  if (-not (Test-Path -LiteralPath $packageDir)) {
    throw 'No se encontr? la carpeta ExelciorApolo dentro del paquete portable.'
  }

  Write-Log 'Copiando paquete expandido a staging.'
  Copy-Item -LiteralPath $packageDir -Destination $stagingDir -Recurse -Force
  $newExe = Join-Path $stagingDir $exeName
  if (-not (Test-Path -LiteralPath $newExe)) {
    throw "No se encontr? el ejecutable esperado en el paquete: $newExe"
  }
  Write-Log "Ejecutable validado en staging: $newExe"

  if (Test-Path -LiteralPath $backupDir) {
    Write-Log 'Eliminando backup anterior.'
    Remove-Item -LiteralPath $backupDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  if (Test-Path -LiteralPath $installDir) {
    Write-Log 'Moviendo instalaci?n actual a backup.'
    Move-Item -LiteralPath $installDir -Destination $backupDir -Force
  }
  Write-Log 'Moviendo staging a instalaci?n final.'
  Move-Item -LiteralPath $stagingDir -Destination $installDir -Force

  $targetExe = Join-Path $installDir $exeName
  if (-not (Test-Path -LiteralPath $targetExe)) {
    if (Test-Path -LiteralPath $installDir) {
      Remove-Item -LiteralPath $installDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $backupDir) {
      Move-Item -LiteralPath $backupDir -Destination $installDir -Force
    }
    throw "La actualizaci?n no dej? un ejecutable v?lido en: $targetExe"
  }
  Write-Log "Instalaci?n final v?lida: $targetExe"

  $desktopDirs = @(
    [Environment]::GetFolderPath('Desktop'),
    [Environment]::GetFolderPath('CommonDesktopDirectory')
  ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

  foreach ($desktopDir in $desktopDirs) {
    Write-Log "Saneando accesos directos en: $desktopDir"
    foreach ($shortcutName in $desktopNames) {
      $shortcutPath = Join-Path $desktopDir $shortcutName
      if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force -ErrorAction SilentlyContinue
      }
    }
    foreach ($exeFileName in $desktopExeNames) {
      $desktopExePath = Join-Path $desktopDir $exeFileName
      if ((Test-Path -LiteralPath $desktopExePath) -and ($desktopExePath -ne $targetExe)) {
        Remove-Item -LiteralPath $desktopExePath -Force -ErrorAction SilentlyContinue
      }
    }
  }

  $desktopDir = [Environment]::GetFolderPath('Desktop')
  if ($desktopDir -and (Test-Path -LiteralPath $desktopDir)) {
    Write-Log 'Recreando acceso directo de escritorio.'
    $shortcutPath = Join-Path $desktopDir $desktopNames[0]
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $targetExe
    $Shortcut.WorkingDirectory = $installDir
    $Shortcut.IconLocation = "$targetExe,0"
    $Shortcut.Save()
  }

  if (Test-Path -LiteralPath $backupDir) {
    Write-Log 'Eliminando backup antiguo.'
    Remove-Item -LiteralPath $backupDir -Recurse -Force -ErrorAction SilentlyContinue
  }

  Write-Log 'Relanzando ejecutable actualizado.'
  Save-State -status 'applied'
  Start-Process -FilePath $targetExe -WorkingDirectory $installDir
} catch {
  Write-Log "Fallo de parche portable: $($_.Exception.Message)"
  Save-State -status 'failed' -errorMessage $_.Exception.Message
  throw
}
"""
    helper_script = helper_script.replace("__CONFIG_PATH__", str(config_path).replace('\\', '\\\\'))
    helper_script = helper_script.replace("__LOG_PATH__", str(log_path).replace('\\', '\\\\'))
    helper_path.write_text(helper_script.strip(), encoding="utf-8")
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper_path),
        ],
        cwd=str(session_root),
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
            verify_downloaded_asset(asset_path, release_info)
            on_ready(asset_path)
        except Exception as exc:
            logging.exception("Fallo la descarga del instalador")
            on_error(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def release_info_to_json(release_info: Dict[str, str]) -> str:
    return json.dumps(release_info, ensure_ascii=False, indent=2)
