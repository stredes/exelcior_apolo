# app/printer/printer_fedex.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import (
    prepare_fedex_dataframe,        # limpieza/dedup principal (si existe tracking)
    insertar_bloque_firma_ws,
    agregar_footer_info_ws,
    formatear_tabla_ws,
)

# ------------------------- Utilidades internas (permisivo) -------------------------

def _colname_map(df: pd.DataFrame) -> dict:
    return {str(c).strip().lower(): c for c in df.columns}

def _heur_total_piezas(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    cmap = _colname_map(df)
    candidatos = [
        "piezas", "bultos", "numberofpackages", "num_packages",
        "cantidad", "total piezas", "total_piezas", "total_bultos"
    ]
    for key in candidatos:
        if key in cmap:
            serie = pd.to_numeric(df[cmap[key]], errors="coerce")
            return int(serie.fillna(0).sum())
    return int(len(df))

def _fallback_permisivo(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str], int]:
    df_out = (df or pd.DataFrame()).copy()
    total_piezas = _heur_total_piezas(df_out)
    return df_out, None, total_piezas

def _enviar_a_impresora_flexible(path: Path, config: Optional[dict]) -> None:
    """
    Llama a enviar_a_impresora tolerando distintas firmas:
      - enviar_a_impresora(path, printer_name=...)
      - enviar_a_impresora(path, printer=...)
      - enviar_a_impresora(path, <printer_name_posicional>)
      - enviar_a_impresora(path)
    """
    printer_name = None
    if isinstance(config, dict):
        # soporta claves comunes
        printer_name = config.get("printer_name") or config.get("printer") or config.get("impresora")

    # 1) keyword 'printer_name'
    if printer_name:
        try:
            return enviar_a_impresora(path, printer_name=printer_name)
        except TypeError:
            pass
        # 2) keyword 'printer'
        try:
            return enviar_a_impresora(path, printer=printer_name)
        except TypeError:
            pass
        # 3) posicional
        try:
            return enviar_a_impresora(path, printer_name)
        except TypeError:
            pass

    # 4) sin parámetro (impresora predeterminada del SO)
    return enviar_a_impresora(path)

# -----------------------------------------------------------------------------------

def print_fedex(file_path, config, df: pd.DataFrame):
    """
    Genera un informe FedEx profesional:
      - Dedup por Tracking Number (si hay columna válida).
      - Pie con TOTAL PIEZAS + timestamp.
      - Bloque de firma y formato de tabla.
      - **Modo permisivo**: si no se puede deduplicar, imprime el DF original.
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de FedEx está vacío y no se puede imprimir.")

        # 1) Preparar datos (limpieza / dedup)
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
                f"[FedEx] Columna tracking usada: '{id_col}'. Filas tras dedup: {filas}. "
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

        # 2) Título
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA FEDEX - {fecha_actual}"

        # 3) Excel temporal base
        tmp_path: Path = generar_excel_temporal(df_out, titulo, sheet_name="FedEx")
        log_evento(f"📄 Archivo temporal generado para impresión FedEx: {tmp_path}", "info")

        # 4) Post-procesar con openpyxl
        wb = load_workbook(tmp_path)
        try:
            ws = wb.active
            formatear_tabla_ws(ws)
            insertar_bloque_firma_ws(ws)
            agregar_footer_info_ws(ws, total_piezas)
            wb.save(tmp_path)
        finally:
            wb.close()

        # 5) Imprimir con wrapper flexible
        _enviar_a_impresora_flexible(tmp_path, config)

        log_evento("✅ Impresión de listado FedEx completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado FedEx: {error}", "error")
        raise RuntimeError(f"Error en impresión FedEx: {error}")
