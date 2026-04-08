# app/printer/printer_fedex.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import os
import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import (
    generar_excel_temporal,
    enviar_a_impresora,
    enviar_a_impresora_configurable,
)
from app.printer.printer_tools import (
    prepare_fedex_dataframe,        # limpieza/dedup principal (si existe tracking)
    insertar_bloque_firma_ws,
    agregar_footer_info_ws,
    formatear_tabla_ws,
)

# =============================================================================
#                    Utilidades internas (modo permisivo)
# =============================================================================

def _colname_map(df: pd.DataFrame) -> Dict[str, str]:
    """Mapa 'nombre en minúscula' -> 'nombre real' para búsqueda flexible."""
    return {str(c).strip().lower(): c for c in df.columns}

def _find_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    """Devuelve la primera columna existente (case-insensitive) de una lista de candidatos."""
    if df is None or df.empty:
        return None
    cmap = _colname_map(df)
    for name in candidates:
        key = name.strip().lower()
        if key in cmap:
            return cmap[key]
    return None

def _agg_mode() -> str:
    """
    Modo de agregación coherente con printer_tools.prepare_fedex_dataframe:
    EXCELCIOR_FEDEX_BULTOS_AGG = last|max|min|sum  (default: last)
    """
    return os.environ.get("EXCELCIOR_FEDEX_BULTOS_AGG", "last").lower()


def _parse_quantity_series(series: pd.Series, default: int = 0) -> pd.Series:
    """Convierte cantidades a enteros preservando el valor real del Excel."""
    if series is None:
        return pd.Series([], dtype=int)

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any():
        extracted = (
            series.astype("string")
            .fillna("")
            .str.replace(",", ".", regex=False)
            .str.extract(r"(-?\d+\.?\d*)")[0]
        )
        fallback_numeric = pd.to_numeric(extracted, errors="coerce")
        numeric = numeric.fillna(fallback_numeric)

    numeric = numeric.fillna(default)
    return numeric.round().astype(int)

def _agg_series_bultos(series: pd.Series) -> int:
    """Agrega una serie de BULTOS de forma robusta según _agg_mode()."""
    b = _parse_quantity_series(series, default=0)
    if b.empty:
        return 0
    mode = _agg_mode()
    if mode == "sum":
        return int(b.sum())
    if mode == "max":
        return int(b.max())
    if mode == "min":
        return int(b.min())
    # last (determinista si se ordena antes)
    return int(b.iloc[-1])

def _heur_total_piezas(df: pd.DataFrame) -> int:
    """
    Heurística estable:
    - Si existe una columna de Tracking y una de BULTOS/PIEZAS, consolidar por Tracking usando _agg_series_bultos.
    - Si sólo existe BULTOS/PIEZAS, sumar (asegurando mínimo 1).
    - Si no, usar len(df).
    """
    if df is None or df.empty:
        return 0

    # Detectar columnas probables
    tracking_col = _find_col(df,
        "mastertrackingnumber", "piecetrackingnumber", "trackingnumber",
        "tracking number", "tracking", "track", "codigo rastreo", "cod rastreo"
    )
    bultos_col = _find_col(df,
        "bultos", "piezas", "numberofpackages", "num_packages",
        "packages", "piececount", "cantidad", "total piezas", "total_piezas", "total_bultos"
    )

    if bultos_col is not None:
        b = _parse_quantity_series(df[bultos_col], default=0)
        if tracking_col:
            # Consolidar por tracking para NO inflar por duplicados
            tmp = (
                df.assign(__b=b)
                  .sort_values([tracking_col], kind="stable")
                  .groupby(tracking_col)["__b"]
                  .apply(_agg_series_bultos)
                  .reset_index(drop=True)
            )
            return int(tmp.sum()) if not tmp.empty else int(b.sum())
        return int(b.sum())

    # Último recurso: contar filas
    return int(len(df))

def _fallback_permisivo(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str], int]:
    """
    Modo permisivo: no tocamos el DF (más que clonar) y calculamos total de piezas
    con la heurística robusta (que evita inflar por duplicados si hay tracking).
    """
    df_out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    total_piezas = _heur_total_piezas(df_out)
    return df_out, None, total_piezas

# =============================================================================
#             Envío a impresora (resuelve impresora/timeout/logs)
# =============================================================================

def _enviar_a_impresora_flexible(path: Path, config: Optional[dict]) -> None:
    """
    Adaptador de compatibilidad para no romper llamadas existentes.
    """
    cfg = config if isinstance(config, dict) else {}
    if not any(k in cfg for k in ("printer_name", "printer", "impresora", "print_timeout_s")):
        # Compatibilidad con tests y llamadas históricas.
        return enviar_a_impresora(path)
    return enviar_a_impresora_configurable(path, config=config, default_timeout_s=120)

# =============================================================================
#                              Flujo principal
# =============================================================================

def print_fedex(file_path: Path, config: Optional[Dict[str, Any]], df: pd.DataFrame):
    """
    Genera un informe FedEx profesional:
      - Dedup/consolidación por Tracking Number (si hay columna válida).
      - Pie con TOTAL PIEZAS + timestamp.
      - Bloque de firma y formato de tabla.
      - **Modo permisivo**: si falla la preparación, imprime el DF original pero con
        total_piezas calculado por heurística robusta (sin inflar por duplicados).
      - Opcional: fallback a PDF si 'fallback_pdf' en config (requiere helpers en impression_tools).
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de FedEx está vacío y no se puede imprimir.")

        # ---------------- 1) Preparar datos (limpieza / dedup) ----------------
        try:
            df_out, id_col, total_piezas = prepare_fedex_dataframe(df)
            if df_out is None or df_out.empty:
                log_evento("[FedEx] DF vacío tras preparación. Activando modo permisivo.", "warning")
                df_out, id_col, total_piezas = _fallback_permisivo(df)
        except Exception as e:
            log_evento(f"[FedEx] prepare_fedex_dataframe falló: {e}. Activando modo permisivo.", "warning")
            df_out, id_col, total_piezas = _fallback_permisivo(df)

        filas = len(df_out)
        if id_col:
            log_evento(
                f"[FedEx] Tracking usado: '{id_col}'. Filas tras consolidación: {filas}. "
                f"Total piezas: {total_piezas}.",
                "info",
            )
        else:
            log_evento(
                f"[FedEx] Sin columna de tracking válida. Filas: {filas}. "
                f"Total piezas (heurística): {total_piezas}.",
                "warning",
            )

        if df_out is None or df_out.empty:
            raise ValueError("No hay filas para imprimir, incluso en modo permisivo.")

        # ---------------- 2) Título ----------------
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA FEDEX - {fecha_actual}"

        # ---------------- 3) Excel temporal base ----------------
        tmp_path: Path = generar_excel_temporal(df_out, titulo, sheet_name="FedEx")
        log_evento(f"📄 Archivo temporal generado para impresión FedEx: {tmp_path}", "info")

        # ---------------- 4) Post-procesar con openpyxl ----------------
        wb = load_workbook(tmp_path)
        try:
            ws = wb.active
            formatear_tabla_ws(ws)
            insertar_bloque_firma_ws(ws, total_piezas)
            agregar_footer_info_ws(ws, total_piezas)
            wb.save(tmp_path)
        finally:
            wb.close()

        # ---------------- 5) Imprimir (XLSX) ----------------
        try:
            _enviar_a_impresora_flexible(tmp_path, config)
            log_evento("✅ Impresión de listado FedEx (XLSX) completada correctamente.", "info")
            return
        except Exception as e_xlsx:
            log_evento(f"⚠️ Falló impresión XLSX: {e_xlsx}", "warning")

            # Fallback PDF opcional
            fallback_pdf = bool(config.get("fallback_pdf")) if isinstance(config, dict) else False
            if not fallback_pdf:
                raise  # Propaga el error si no hay fallback habilitado

            # ---------------- 6) Fallback a PDF (opcional) ----------------
            try:
                # Import tardío para no romper si no existen aún
                from app.core.impression_tools import convert_xlsx_to_pdf, enviar_pdf_a_impresora
            except Exception as imp_err:
                raise RuntimeError(
                    "Fallback PDF habilitado pero faltan helpers en impression_tools. "
                    f"Detalle: {imp_err}"
                )

            try:
                pdf_path = convert_xlsx_to_pdf(tmp_path)  # usa soffice --convert-to pdf
                log_evento(f"🧾 PDF generado para fallback: {pdf_path}", "info")
                enviar_pdf_a_impresora(pdf_path)
                log_evento("✅ Impresión de listado FedEx (PDF fallback) completada correctamente.", "info")
                return
            except Exception as e_pdf:
                log_evento(f"❌ Falló impresión PDF (fallback): {e_pdf}", "error")
                raise  # Propagar al caller

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado FedEx: {error}", "error")
        raise RuntimeError(f"Error en impresión FedEx: {error}")
