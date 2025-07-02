import re
import json
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import suppress

# Configuración de ruta global para el archivo de usuario
CONFIG_PATH = Path("config/user_config.json")
logger = logging.getLogger(__name__)

# ------------------ Gestión de configuración ------------------

def cargar_config_usuario() -> dict:
    """Carga la configuración del usuario desde archivo JSON."""
    if CONFIG_PATH.exists():
        with suppress(Exception):
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    return {}

def guardar_config_usuario(config: dict):
    """Guarda la configuración del usuario en archivo JSON."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"[Autoloader] Error al guardar configuración: {e}")

def set_carpeta_descarga_personalizada(ruta: Path, modo: str):
    """Establece una carpeta personalizada para guardar archivos según el modo."""
    config = cargar_config_usuario()
    config.setdefault("carpetas_por_modo", {})[modo] = str(ruta.resolve())
    guardar_config_usuario(config)
    logger.info(f"[Autoloader] Carpeta personalizada establecida para modo '{modo}': {ruta}")

def get_carpeta_descarga_personalizada(modo: str) -> Path:
    """Obtiene la carpeta personalizada para el modo o retorna ~/Descargas."""
    config = cargar_config_usuario()
    ruta_config = config.get("carpetas_por_modo", {}).get(modo)
    if ruta_config and Path(ruta_config).exists():
        return Path(ruta_config)
    return Path.home() / "Descargas"

# ------------------ Detección por nombre de archivo ------------------

def is_urbano_pattern(filename: str) -> bool:
    """Detecta si el nombre corresponde a un archivo Urbano (9 dígitos exactos)."""
    return re.fullmatch(r"\d{9}", Path(filename).stem) is not None

def is_listado_pattern(filename: str) -> bool:
    """Detecta si el nombre corresponde a un archivo de listado con patrón esperado."""
    return re.fullmatch(r"lista_doc_venta_\d{8}_\d{6}", Path(filename).stem) is not None

def is_fedex_pattern(filename: str) -> bool:
    """Detecta si el nombre corresponde a un archivo FedEx con patrón esperado."""
    return re.fullmatch(r"shipment_report_\d{4}-\d{2}-\d{2}", Path(filename).stem.lower()) is not None

def matches_mode(filename: str, mode: str) -> bool:
    """Verifica si el nombre del archivo coincide con el modo especificado."""
    name = filename.lower()
    return (
        (mode == "fedex" and ("fedex" in name or is_fedex_pattern(filename))) or
        (mode == "listados" and ("listado" in name or "venta" in name or is_listado_pattern(filename))) or
        (mode == "urbano" and is_urbano_pattern(filename))
    )

# ------------------ Carga del archivo más reciente ------------------

def find_latest_file_by_mode(
    mode: str,
    download_folder: Optional[Path] = None,
    allowed_extensions: Optional[List[str]] = None
) -> Tuple[Optional[Path], str]:
    """
    Busca el archivo más reciente que coincida con el modo.
    Devuelve (archivo, estado): estado puede ser 'ok', 'empty_folder', 'no_match'
    """
    if download_folder is None:
        download_folder = get_carpeta_descarga_personalizada(mode)
    if allowed_extensions is None:
        allowed_extensions = ['.xlsx', '.xls', '.csv']

    if not download_folder.exists():
        logger.warning(f"[Autoloader] Carpeta no encontrada: {download_folder}")
        return None, "empty_folder"

    archivos = list(download_folder.glob("*"))
    if not archivos:
        logger.info(f"[Autoloader] Carpeta vacía: {download_folder}")
        return None, "empty_folder"

    archivos_filtrados = [
        f for f in archivos
        if f.suffix.lower() in allowed_extensions and matches_mode(f.name, mode)
    ]

    if not archivos_filtrados:
        logger.info(f"[Autoloader] No hay coincidencias para modo '{mode}' en {download_folder}")
        return None, "no_match"

    archivo_mas_reciente = max(archivos_filtrados, key=lambda f: f.stat().st_mtime)
    logger.info(f"[Autoloader] Archivo más reciente para '{mode}': {archivo_mas_reciente.name}")
    return archivo_mas_reciente, "ok"
