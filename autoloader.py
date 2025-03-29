import re
from pathlib import Path
from typing import Optional, List, Tuple


def is_urbano_pattern(filename: str) -> bool:
    return re.fullmatch(r"\d{9}", Path(filename).stem) is not None


def is_listado_pattern(filename: str) -> bool:
    return re.match(r"^lista_doc_venta_\d{8}_\d{6}$", Path(filename).stem) is not None


def is_fedex_pattern(filename: str) -> bool:
    return re.match(r"^shipment_report_\d{4}-\d{2}-\d{2}$", Path(filename).stem.lower()) is not None


def matches_mode(filename: str, mode: str) -> bool:
    name = filename.lower()
    if mode == "fedex":
        return "fedex" in name or is_fedex_pattern(filename)
    elif mode == "listados":
        return is_listado_pattern(filename) or "listado" in name or "venta" in name
    elif mode == "urbano":
        return is_urbano_pattern(filename)
    return False


def find_latest_file_by_mode(
    mode: str,
    download_folder: Optional[Path] = None,
    allowed_extensions: Optional[List[str]] = None
) -> Tuple[Optional[Path], str]:
    """
    Devuelve (archivo, estado): estado puede ser 'ok', 'empty_folder', 'no_match'
    """
    if download_folder is None:
        download_folder = Path.home() / "Descargas"
    if allowed_extensions is None:
        allowed_extensions = ['.xlsx', '.xls', '.csv']

    if not download_folder.exists():
        return None, "empty_folder"

    archivos = list(download_folder.glob("*"))
    if not archivos:
        return None, "empty_folder"

    archivos_filtrados = [
        f for f in archivos
        if f.suffix.lower() in allowed_extensions and matches_mode(f.name, mode)
    ]

    if not archivos_filtrados:
        return None, "no_match"

    archivos_ordenados = sorted(archivos_filtrados, key=lambda f: f.stat().st_mtime, reverse=True)
    return archivos_ordenados[0], "ok"
