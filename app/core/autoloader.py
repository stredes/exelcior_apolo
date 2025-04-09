import re
import json
from pathlib import Path
from typing import Optional, List, Tuple

from app.utils.utils import load_config
from app.core.logger_bod1 import capturar_log_bod1

CONFIG_PATH = Path("config/user_config.json")


# --- Configuración persistente por modo ---

def cargar_config_usuario() -> dict:
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_config_usuario(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def set_carpeta_descarga_personalizada(ruta: Path, modo: str):
    config = cargar_config_usuario()
    config.setdefault("carpetas_por_modo", {})
    config["carpetas_por_modo"][modo] = str(ruta.resolve())
    guardar_config_usuario(config)

def get_carpeta_descarga_personalizada(modo: str) -> Path:
    config = cargar_config_usuario()
    ruta_config = config.get("carpetas_por_modo", {}).get(modo)
    if ruta_config and Path(ruta_config).exists():
        return Path(ruta_config)
    return Path.home() / "Descargas"


# --- Detección por patrón de nombre de archivo ---

def is_urbano_pattern(filename: str, digit_lengths: List[int]) -> bool:
    stem = Path(filename).stem
    return stem.isdigit() and len(stem) in digit_lengths

def is_listado_pattern(filename: str) -> bool:
    return re.match(r"^lista_doc_venta_\d{8}_\d{6}$", Path(filename).stem) is not None

def is_fedex_pattern(filename: str) -> bool:
    return re.match(r"^shipment_report_\d{4}-\d{2}-\d{2}$", Path(filename).stem.lower()) is not None


def matches_mode(filename: str, mode: str, config: dict) -> bool:
    name = filename.lower()

    if mode == "fedex":
        return "fedex" in name or is_fedex_pattern(filename)
    elif mode == "listados":
        return is_listado_pattern(filename) or "listado" in name or "venta" in name
    elif mode == "urbano":
        digit_lengths = config.get(mode, {}).get("nombre_archivo_digitos", [9, 10])
        return is_urbano_pattern(filename, digit_lengths)

    return False


# --- Autocarga de archivo más reciente ---

def find_latest_file_by_mode(
    mode: str,
    download_folder: Optional[Path] = None,
    allowed_extensions: Optional[List[str]] = None
) -> Tuple[Optional[Path], str]:
    """
    Devuelve (archivo, estado): estado puede ser 'ok', 'empty_folder', 'no_match'
    """
    config = load_config()

    if download_folder is None:
        download_folder = get_carpeta_descarga_personalizada(mode)
    if allowed_extensions is None:
        allowed_extensions = ['.xlsx', '.xls', '.csv']

    if not download_folder.exists():
        capturar_log_bod1(f"📂 Carpeta de descargas no encontrada: {download_folder}", "warning")
        return None, "empty_folder"

    archivos = list(download_folder.glob("*"))
    if not archivos:
        return None, "empty_folder"

    archivos_filtrados = [
        f for f in archivos
        if f.suffix.lower() in allowed_extensions and matches_mode(f.name, mode, config)
    ]

    if not archivos_filtrados:
        capturar_log_bod1(f"❌ No hay archivos válidos para el modo '{mode}' en {download_folder}", "warning")
        return None, "no_match"

    archivos_ordenados = sorted(archivos_filtrados, key=lambda f: f.stat().st_mtime, reverse=True)
    capturar_log_bod1(f"✅ Archivo encontrado: {archivos_ordenados[0].name}", "info")
    return archivos_ordenados[0], "ok"
