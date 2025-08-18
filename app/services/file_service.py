# app/services/file_service.py

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

# -------------------- VALIDACIÓN --------------------

def validate_file(path: str | Path) -> Tuple[bool, str]:
    return core_validate(str(path))

# -------------------- PROCESAMIENTO --------------------

def process_file(path_or_df: str | Path | pd.DataFrame,
                 config_columns: dict,
                 mode: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if isinstance(path_or_df, pd.DataFrame):
        df = path_or_df
    else:
        path = Path(path_or_df) if not isinstance(path_or_df, Path) else path_or_df
        df = load_excel(path, config_columns, mode)

    transformed = apply_transformation(df.copy(), config_columns, mode)
    return df, transformed

# -------------------- DISPATCHER DE IMPRESIÓN --------------------

printer_map: Dict[str, Callable] = {}

def _safe_register(name: str, module, func_name: str):
    """Registra en el mapa si el módulo tiene la función esperada."""
    if hasattr(module, func_name):
        printer_map[name] = getattr(module, func_name)
        logger.info(f"[dispatcher] Registrado printer '{name}' -> {module.__name__}.{func_name}")
    else:
        logger.warning(f"[dispatcher] El módulo {module.__name__} no expone '{func_name}'")

# Registro “eager”
_safe_register("fedex", printer_fedex, "print_fedex")
_safe_register("urbano", printer_urbano, "print_urbano")
_safe_register("listados", printer_listados, "print_listados")
_safe_register("etiquetas", printer_etiquetas, "print_etiquetas")
_safe_register("inventario_codigo", printer_inventario_codigo, "print_inventario_codigo")
_safe_register("inventario_ubicacion", printer_inventario_ubicacion, "print_inventario_ubicacion")

logger.info(f"Printers registrados (eager): {list(printer_map.keys())}")

def _normalize_mode(mode: Optional[str]) -> str:
    return (mode or "").strip().lower()

def _lazy_load_printer(mode_norm: str) -> Optional[Callable]:
    """
    Cargador perezoso: intenta importar app.printer.printer_<modo>
    y obtener la función print_<modo>. Devuelve la callable o None.
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
    Devuelve la función de impresión. Si no está registrada, intenta lazy-load.
    """
    mode_norm = _normalize_mode(mode)
    fn = printer_map.get(mode_norm)
    if fn:
        return fn
    # Intento perezoso (cubre desórdenes de import, paquetes parcializados, etc.)
    return _lazy_load_printer(mode_norm)

def print_document(mode: str,
                   df: pd.DataFrame,
                   config_columns: dict,
                   file_path: Optional[str | Path] = None):
    """
    Invoca la función de impresión del modo dado.
    Todas deben aceptar firma: (file_path, config, df).
    """
    fn = get_printer(mode)
    if not fn:
        mode_norm = _normalize_mode(mode)
        raise RuntimeError(f"No se encontró función para el modo: {mode_norm}")
    return fn(file_path, config_columns, df)
