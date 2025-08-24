# app/services/file_service.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import importlib
from pathlib import Path
from typing import Tuple, Optional, Callable, Dict

import pandas as pd

from app.core.excel_processor import (
    validate_file as core_validate,
    load_excel,
    apply_transformation,
)

# Import “eager” (si alguno falla, el lazy loader lo cubrirá)
from app.printer import (
    printer_fedex,
    printer_urbano,
    printer_listados,
    printer_etiquetas,
    printer_inventario_codigo,
    printer_inventario_ubicacion,
)

logger = logging.getLogger(__name__)

# =============================================================================
#                               VALIDACIÓN
# =============================================================================

def validate_file(path: str | Path) -> Tuple[bool, str]:
    """Valida archivo de entrada (existencia, extensión, apertura básica)."""
    return core_validate(str(path))


# =============================================================================
#                              PROCESAMIENTO
# =============================================================================

def process_file(
    path_or_df: str | Path | pd.DataFrame,
    config_columns: dict,
    mode: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carga y transforma el archivo/DF según el modo y la configuración.
    Devuelve (df_original, df_transformado).
    """
    try:
        if isinstance(path_or_df, pd.DataFrame):
            df = path_or_df.copy()
            logger.info("[process_file] Recibido DataFrame en memoria")
        else:
            path = Path(path_or_df) if not isinstance(path_or_df, Path) else path_or_df
            logger.info(f"[process_file] Cargando archivo: {path}")
            df = load_excel(path, config_columns, mode)

        transformed = apply_transformation(df.copy(), config_columns, mode)
        logger.info(f"[process_file] Transformación OK. Filas: src={len(df)}, out={len(transformed)}")
        return df, transformed

    except Exception as e:
        logger.exception(f"[process_file] Error procesando archivo/DF (modo={mode})")
        raise


# =============================================================================
#                          DISPATCHER DE IMPRESIÓN
# =============================================================================

# Mapa de funciones de impresión registradas
printer_map: Dict[str, Callable] = {}

def _safe_register(name: str, module, func_name: str):
    """Registra printer si el módulo expone la función esperada."""
    try:
        if hasattr(module, func_name):
            printer_map[name] = getattr(module, func_name)
            logger.info(f"[dispatcher] Registrado '{name}' -> {module.__name__}.{func_name}")
        else:
            logger.warning(f"[dispatcher] {module.__name__} no expone '{func_name}'")
    except Exception:
        logger.exception(f"[dispatcher] Falló registro para '{name}'")


# Registro eager (carga directa en import)
_safe_register("fedex", printer_fedex, "print_fedex")
_safe_register("urbano", printer_urbano, "print_urbano")
_safe_register("listados", printer_listados, "print_listados")
_safe_register("etiquetas", printer_etiquetas, "print_etiquetas")
_safe_register("inventario_codigo", printer_inventario_codigo, "print_inventario_codigo")
_safe_register("inventario_ubicacion", printer_inventario_ubicacion, "print_inventario_ubicacion")

logger.info(f"[dispatcher] Printers registrados (eager): {sorted(printer_map.keys())}")


def _normalize_mode(mode: Optional[str]) -> str:
    """Normaliza el nombre del modo y soporta algunos alias comunes."""
    m = (mode or "").strip().lower()
    aliases = {
        "inventario-codigo": "inventario_codigo",
        "inventario-códig": "inventario_codigo",
        "inventario_ubic": "inventario_ubicacion",
    }
    return aliases.get(m, m)


def _lazy_load_printer(mode_norm: str) -> Optional[Callable]:
    """
    Carga perezosa: importa app.printer.printer_<modo> y obtiene print_<modo>.
    Devuelve la callable o None si falla.
    """
    try:
        module_name = f"app.printer.printer_{mode_norm}"
        func_name = f"print_{mode_norm}"
        mod = importlib.import_module(module_name)
        if hasattr(mod, func_name):
            fn = getattr(mod, func_name)
            printer_map[mode_norm] = fn
            logger.info(f"[dispatcher] Lazy-registered '{mode_norm}' -> {module_name}.{func_name}")
            return fn
        logger.warning(f"[dispatcher] {module_name} no tiene '{func_name}'")
    except Exception as e:
        logger.error(f"[dispatcher] Lazy load falló para modo '{mode_norm}': {e}")
    return None


def get_printer(mode: Optional[str]) -> Optional[Callable]:
    """
    Devuelve la función de impresión del modo. Si no está, intenta lazy-load.
    """
    mode_norm = _normalize_mode(mode)
    fn = printer_map.get(mode_norm)
    if fn:
        return fn
    return _lazy_load_printer(mode_norm)


def print_document(
    mode: str,
    df: pd.DataFrame,
    config_columns: dict,
    file_path: Optional[str | Path] = None
):
    """
    Invoca la función de impresión del modo dado.
    Todas deben aceptar firma: (file_path, config, df).

    NOTA:
    - La preparación específica (dedupe/sumas) se realiza en cada printer_<modo>.
      Ej.: FedEx consolida BULTOS y Urbano suma PIEZAS y agrega pie de página.
    """
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        raise ValueError("No hay datos para imprimir (DataFrame vacío).")

    fn = get_printer(mode)
    if not fn:
        mode_norm = _normalize_mode(mode)
        raise RuntimeError(f"No se encontró función de impresión para el modo: '{mode_norm}'")

    logger.info(f"[print_document] Ejecutando impresora de modo '{_normalize_mode(mode)}'")
    return fn(file_path, config_columns, df)
