# app/services/file_service.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import importlib
import platform
import time
import os
from pathlib import Path
from typing import Tuple, Optional, Callable, Dict, Any
from contextlib import contextmanager

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

# >>> NUEVO: para que la vista previa FedEx consolide igual que la impresión
from app.printer.printer_tools import prepare_fedex_dataframe

logger = logging.getLogger(__name__)

# Impresora fallback para los 3 modos principales (papel común).
FALLBACK_MAIN_PRINTER = "Brother DCP-L5650DN series [b422002bd4a6]"
FORCED_MAIN_MODES = {"listados", "fedex", "urbano"}


def _get_report_printer(cfg: dict) -> str:
    """
    Resuelve la impresora de reportes (papel común) desde config:
    prioridad alta -> baja:
      1) report_printer_name / paper_printer_name
      2) default_printer (legacy)
      3) paths.default_printer (v2)
      4) fallback hardcodeado
    """
    if not isinstance(cfg, dict):
        return FALLBACK_MAIN_PRINTER

    top_level = (
        cfg.get("report_printer_name")
        or cfg.get("paper_printer_name")
        or cfg.get("default_printer")
    )
    if isinstance(top_level, str) and top_level.strip():
        return top_level.strip()

    paths_cfg = cfg.get("paths")
    if isinstance(paths_cfg, dict):
        p = paths_cfg.get("default_printer")
        if isinstance(p, str) and p.strip():
            return p.strip()

    return FALLBACK_MAIN_PRINTER


def _resolve_windows_printer_name(alias: str) -> str:
    base = (alias or "").strip()
    if not base or platform.system() != "Windows":
        return base
    try:
        import win32print  # type: ignore

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        names = []
        for item in win32print.EnumPrinters(flags):
            try:
                n = str(item[2]).strip()
            except Exception:
                continue
            if n:
                names.append(n)
        low = base.lower()
        for n in names:
            if n.lower() == low:
                return n
        for n in names:
            if low in n.lower() or n.lower() in low:
                return n
    except Exception:
        pass
    return base


@contextmanager
def _temporary_windows_default_printer(printer_name: str):
    if platform.system() != "Windows" or not printer_name:
        yield
        return
    old_default = None
    switched = False
    try:
        import win32print  # type: ignore

        resolved = _resolve_windows_printer_name(printer_name)
        old_default = win32print.GetDefaultPrinter()
        if resolved:
            win32print.SetDefaultPrinter(resolved)
            switched = True
            logger.info(f"[print_document] Default temporal aplicada: {resolved}")
    except Exception as e:
        logger.warning(f"[print_document] No se pudo forzar default temporal: {e}")
    try:
        yield
    except Exception as e:
        logger.warning(f"[print_document] Error dentro de bloque de impresión: {e}")
        raise
    finally:
        if switched:
            # margen breve para que el spooler tome el trabajo antes de restaurar
            time.sleep(3)
        if old_default:
            try:
                import win32print  # type: ignore

                win32print.SetDefaultPrinter(old_default)
                logger.info(f"[print_document] Default restaurada: {old_default}")
            except Exception:
                pass


@contextmanager
def _temporary_forced_printer_env(printer_name: str):
    """
    Fuerza EXCELCIOR_PRINTER solo durante el bloque para evitar arrastre
    entre etiquetas y reportes.
    """
    old_val = None
    had_old = "EXCELCIOR_PRINTER" in os.environ
    try:
        if had_old:
            old_val = os.environ.get("EXCELCIOR_PRINTER")
        if printer_name:
            os.environ["EXCELCIOR_PRINTER"] = str(printer_name)
        yield
    finally:
        env = os.environ
        if had_old:
            env["EXCELCIOR_PRINTER"] = old_val if old_val is not None else ""
        else:
            env.pop("EXCELCIOR_PRINTER", None)

# =============================================================================
#                               VALIDACIÓN
# =============================================================================

def validate_file(path: str | Path) -> Tuple[bool, str]:
    """Valida archivo de entrada (existencia, extensión, apertura básica)."""
    return core_validate(str(path))


# =============================================================================
#                              PROCESAMIENTO
# =============================================================================

def _normalize_mode(mode: Optional[str]) -> str:
    """Normaliza el nombre del modo y soporta algunos alias comunes."""
    m = (mode or "").strip().lower()
    aliases = {
        "inventario-codigo": "inventario_codigo",
        "inventario-códig": "inventario_codigo",
        "inventario_ubic": "inventario_ubicacion",
    }
    return aliases.get(m, m)


def _sanitize_preview_dataframe(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """
    Limpia filas de resumen no deseadas para la vista previa por modo.
    Actualmente elimina filas 'TOTAL' para urbano.
    """
    if df is None or df.empty:
        return df

    if _normalize_mode(mode) != "urbano":
        return df

    try:
        mask_total = pd.Series(False, index=df.index)
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
            col_values = df[col].astype(str).str.strip().str.upper()
            mask_total = mask_total | (col_values == "TOTAL")
        if mask_total.any():
            return df.loc[~mask_total].reset_index(drop=True)
    except Exception:
        logger.exception("[preview] Error sanitizando filas TOTAL para urbano")
    return df


def build_preview_dataframe(df: pd.DataFrame, config_columns: dict, mode: str) -> pd.DataFrame:
    """
    Pipeline único de negocio para construir DataFrame de vista previa.
    """
    mode_norm = _normalize_mode(mode)
    base_transformed = apply_transformation(df.copy(), config_columns, mode_norm)

    if mode_norm == "fedex":
        try:
            # Fuente única: transformación base + consolidación FedEx
            preview_df, _id_col, _total = prepare_fedex_dataframe(base_transformed)
            if "BULTOS" in preview_df.columns:
                preview_df["BULTOS"] = (
                    pd.to_numeric(preview_df["BULTOS"], errors="coerce").fillna(0).astype(int)
                )
        except Exception:
            logger.exception("[preview] FedEx: error en prepare_fedex_dataframe; usando base_transformed")
            preview_df = base_transformed
    else:
        preview_df = base_transformed

    return _sanitize_preview_dataframe(preview_df, mode_norm)


def compute_preview_stats(df: Optional[pd.DataFrame], mode: str) -> Dict[str, Any]:
    """
    Calcula estadísticas de vista previa de forma uniforme para la UI.
    """
    stats: Dict[str, Any] = {
        "rows": int(len(df) if isinstance(df, pd.DataFrame) else 0),
        "metric_label": None,
        "metric_value": None,
    }

    if not isinstance(df, pd.DataFrame) or df.empty:
        return stats

    mode_norm = _normalize_mode(mode)
    if mode_norm == "fedex" and "BULTOS" in df.columns:
        total = int(pd.to_numeric(df["BULTOS"], errors="coerce").fillna(0).sum())
        stats["metric_label"] = "BULTOS"
        stats["metric_value"] = total
    elif mode_norm == "urbano" and "PIEZAS" in df.columns:
        total = int(pd.to_numeric(df["PIEZAS"], errors="coerce").fillna(0).sum())
        stats["metric_label"] = "PIEZAS"
        stats["metric_value"] = total

    return stats

def process_file(
    path_or_df: str | Path | pd.DataFrame,
    config_columns: dict,
    mode: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carga y transforma el archivo/DF según el modo y la configuración.
    Devuelve (df_original, df_transformado).

    Cambio clave:
    - Para modo 'fedex' la vista previa usa prepare_fedex_dataframe(...) para
      consolidar por masterTrackingNumber y mapear numberOfPackages -> BULTOS,
      igual que la impresión. Así evitas ver '1' por fila en la grilla.
    """
    try:
        mode_norm = _normalize_mode(mode)

        # ---- Carga origen ----
        if isinstance(path_or_df, pd.DataFrame):
            df = path_or_df.copy()
            logger.info("[process_file] Recibido DataFrame en memoria")
        else:
            path = Path(path_or_df) if not isinstance(path_or_df, Path) else path_or_df
            logger.info(f"[process_file] Cargando archivo: {path}")
            df = load_excel(path, config_columns, mode_norm)

        transformed = build_preview_dataframe(df, config_columns, mode_norm)

        logger.info(f"[process_file] Transformación OK. Filas: src={len(df)}, out={len(transformed)}")
        return df, transformed

    except Exception:
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

    mode_norm = _normalize_mode(mode)
    cfg = config_columns if isinstance(config_columns, dict) else {}
    cfg_to_use = cfg

    # Forzar cola física de papel para Listados/FedEx/Urbano.
    if mode_norm in FORCED_MAIN_MODES:
        report_printer = _get_report_printer(cfg)
        cfg_to_use = dict(cfg)
        cfg_to_use["printer_name"] = report_printer
        cfg_to_use["printer"] = report_printer
        cfg_to_use["impresora"] = report_printer
        logger.info(f"[print_document] Impresora forzada para '{mode_norm}': {report_printer}")

    logger.info(f"[print_document] Ejecutando impresora de modo '{mode_norm}'")
    if mode_norm in FORCED_MAIN_MODES:
        forced = _get_report_printer(cfg_to_use)
        with _temporary_forced_printer_env(forced):
            with _temporary_windows_default_printer(forced):
                return fn(file_path, cfg_to_use, df)
    return fn(file_path, cfg_to_use, df)
