# app/printer/printer_urbano.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import (
    prepare_urbano_dataframe,
    insertar_bloque_firma_ws,
    agregar_footer_info_ws,
    formatear_tabla_ws,
)

# ---------------------------------------------------------------------
# Enviar a impresora con compatibilidad de firma:
# ver comentarios en printer_fedex.py
# ---------------------------------------------------------------------
def _send_to_printer_compat(path: Path, printer_name: Optional[str]) -> None:
    try:
        enviar_a_impresora(path, printer_name=printer_name)
        return
    except TypeError:
        pass

    try:
        if printer_name is not None:
            enviar_a_impresora(path, printer_name)
            return
    except TypeError:
        pass

    enviar_a_impresora(path)


def _estimate_total_piezas(df: pd.DataFrame) -> int:
    """
    Busca columnas candidatas y suma sus valores numéricos,
    limpiando textos como '3 piezas' o '2,0'.
    """
    candidatos = ("PIEZAS", "piezas", "Piezas", "BULTOS", "bultos")
    for nombre in candidatos:
        if nombre in df.columns:
            serie = pd.to_numeric(df[nombre], errors="coerce")
            if serie.isna().any():
                extraida = (
                    df[nombre]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .str.extract(r"(\d+\.?\d*)")[0]
                )
                serie = serie.fillna(pd.to_numeric(extraida, errors="coerce"))
            serie = serie.fillna(0).clip(lower=0)
            return int(serie.sum().round())
    return int(len(df.index))


def print_urbano(file_path, config, df: pd.DataFrame):
    """
    Genera un listado Urbano profesional:
      - Normaliza/valida datos (GUIA | CLIENTE | LOCALIDAD | PIEZAS | COD RASTREO)
      - Suma total de PIEZAS
      - Encabezados, bordes y anchos mínimos
      - Bloque de firma con líneas
      - Pie con timestamp y 'Total Piezas'
      - Imprime el archivo resultante
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de Urbano está vacío y no se puede imprimir.")

        # 1) Preparar datos (limpieza + totales)
        df_out, total_piezas = prepare_urbano_dataframe(df)
        if df_out is None or df_out.empty:
            df_out = df.copy()
            total_piezas = _estimate_total_piezas(df_out)

        filas = len(df_out)
        log_evento(f"[Urbano] Filas a imprimir: {filas}. Total PIEZAS: {total_piezas}.", "info")

        # 2) Título
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA URBANO - {fecha_actual}"

        # 3) Excel temporal base
        tmp_path: Path = generar_excel_temporal(df_out, titulo, sheet_name="Urbano")
        log_evento(f"📄 Archivo temporal generado para impresión Urbano: {tmp_path}", "info")

        # 4) Post-procesar con openpyxl: formato + firma + footer
        wb = load_workbook(tmp_path)
        try:
            ws = wb.active
            formatear_tabla_ws(ws)                   # estilo profesional
            insertar_bloque_firma_ws(ws, total_piezas)  # bloque firma con líneas
            agregar_footer_info_ws(ws, total_piezas)    # pie con timestamp + total piezas
            wb.save(tmp_path)
        finally:
            wb.close()

        # 5) Enviar a impresora (compatibilidad de firma)
        printer_name = (config or {}).get("printer_name")
        _send_to_printer_compat(tmp_path, printer_name)

        log_evento("✅ Impresión de listado Urbano completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado Urbano: {error}", "error")
        raise RuntimeError(f"Error en impresión Urbano: {error}")
