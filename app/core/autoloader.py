import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import suppress

# Configuración de ruta global para el archivo de usuario
CONFIG_PATH = Path("app/config/user_config.json")
LEGACY_CONFIG_PATH = Path("config/user_config.json")
logger = logging.getLogger(__name__)

# ------------------ Gestión de configuración ------------------

def cargar_config_usuario() -> dict:
    """Carga la configuración del usuario desde archivo JSON."""
    for p in (CONFIG_PATH, LEGACY_CONFIG_PATH):
        if p.exists():
            with suppress(Exception):
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
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
    """Obtiene la carpeta personalizada para el modo o retorna carpeta de descargas del sistema."""
    config = cargar_config_usuario()
    ruta_config = config.get("carpetas_por_modo", {}).get(modo)
    if ruta_config and Path(ruta_config).exists():
        return Path(ruta_config)
    # Fallback robusto para Windows/ES/EN
    candidatos = [
        Path.home() / "Downloads",
        Path.home() / "Descargas",
        Path.home() / "OneDrive" / "Downloads",
        Path.home() / "OneDrive" / "Descargas",
    ]
    for p in candidatos:
        if p.exists():
            return p
    return Path.home() / "Downloads"

# ------------------ Detección por nombre de archivo ------------------

def is_urbano_pattern(filename: str) -> bool:
    """
    Detecta si el nombre corresponde a un archivo Urbano.
    Soporta códigos numéricos de 8 o 9 dígitos (ej: 19561938, 844317333).
    """
    return re.fullmatch(r"\d{8,9}", Path(filename).stem) is not None

def is_listado_pattern(filename: str) -> bool:
    """Detecta si el nombre corresponde a un archivo de listado con patrón esperado."""
    stem = Path(filename).stem.lower()
    return (
        re.fullmatch(r"lista_doc_venta_\d{8}_\d{6}", stem) is not None
        or "lista_doc" in stem
    )

def is_fedex_pattern(filename: str) -> bool:
    """Detecta si el nombre corresponde a un archivo FedEx con patrón esperado."""
    stem = Path(filename).stem.lower()
    return (
        re.fullmatch(r"shipment_report_\d{4}-\d{2}-\d{2}", stem) is not None
        or "shipment" in stem
    )

def matches_mode(filename: str, mode: str) -> bool:
    """Verifica si el nombre del archivo coincide con el modo especificado."""
    name = Path(filename).stem.lower()
    return (
        (mode == "fedex" and is_fedex_pattern(filename)) or
        (mode == "listados" and is_listado_pattern(filename)) or
        (mode == "urbano" and is_urbano_pattern(filename))
    )


def _extract_datetime_from_filename(path: Path, mode: str) -> Optional[datetime]:
    """
    Intenta extraer una fecha/hora del nombre para priorizar archivos reales de descarga.
    """
    stem = path.stem
    low = stem.lower()
    try:
        if mode == "listados":
            # lista_doc_venta_YYYYMMDD_HHMMSS
            m = re.search(r"lista_doc_venta_(\d{8})_(\d{6})", low)
            if m:
                return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y%m%d %H%M%S")
        elif mode == "fedex":
            # Shipment_Report_YYYY-MM-DD
            m = re.search(r"shipment_report_(\d{4}-\d{2}-\d{2})", low)
            if m:
                return datetime.strptime(m.group(1), "%Y-%m-%d")
    except Exception:
        return None
    return None


def _pick_latest_file(files: List[Path], mode: str) -> Path:
    now_date = datetime.now().date()

    def rank(f: Path):
        st = f.stat()
        mtime = datetime.fromtimestamp(st.st_mtime)
        ctime = datetime.fromtimestamp(st.st_ctime)
        name_dt = _extract_datetime_from_filename(f, mode)
        # Fecha principal: la del nombre si existe, si no mtime.
        primary = name_dt or mtime
        # Prioriza archivos del día por fecha principal o timestamps del sistema.
        is_today = int(
            primary.date() == now_date
            or mtime.date() == now_date
            or ctime.date() == now_date
        )
        return (is_today, primary, mtime, ctime)

    return max(files, key=rank)

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

    archivos = [
        f for f in download_folder.glob("*")
        if f.is_file() and not f.name.startswith("~$")
    ]
    if not archivos:
        logger.info(f"[Autoloader] Carpeta vacía: {download_folder}")
        return None, "empty_folder"

    archivos_filtrados = [
        f for f in archivos
        if f.suffix.lower() in allowed_extensions and matches_mode(f.name, mode)
    ]

    # Si no hay match por patrón de nombre, usar fallback por fecha (workflow real usuario).
    if not archivos_filtrados:
        archivos_filtrados = [f for f in archivos if f.suffix.lower() in allowed_extensions]
        if not archivos_filtrados:
            logger.info(f"[Autoloader] No hay coincidencias para modo '{mode}' en {download_folder}")
            return None, "no_match"
        logger.warning(
            f"[Autoloader] Sin match por patrón para modo '{mode}'. "
            f"Usando fallback por fecha en carpeta: {download_folder}"
        )

    archivo_mas_reciente = _pick_latest_file(archivos_filtrados, mode)
    logger.info(f"[Autoloader] Archivo más reciente para '{mode}': {archivo_mas_reciente.name}")
    return archivo_mas_reciente, "ok"
