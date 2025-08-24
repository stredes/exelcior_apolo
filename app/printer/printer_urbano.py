# app/printer/printer_urbano.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import (
    prepare_urbano_dataframe,   # normaliza columnas y calcula total PIEZAS
    formatear_tabla_ws,         # bordes, anchos, encabezados
    insertar_bloque_firma_ws,   # líneas reales para nombre/firma
    agregar_footer_info_ws,     # pie: "Impresa el ... | Total Piezas: X"
)


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
            raise ValueError("No hay filas válidas para imprimir Urbano.")

        filas = len(df_out)
        log_evento(f"[Urbano] Filas tras limpieza: {filas}. Total PIEZAS: {total_piezas}.", "info")

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
            formatear_tabla_ws(ws)                     # estilo profesional
            insertar_bloque_firma_ws(ws)               # bloque firma con líneas
            agregar_footer_info_ws(ws, total_piezas)   # pie con timestamp + total piezas
            wb.save(tmp_path)
        finally:
            wb.close()

        # 5) Enviar a impresora (permite definir impresora en config)
        printer_name = (config or {}).get("printer_name")
        enviar_a_impresora(tmp_path, printer_name=printer_name)

        log_evento("✅ Impresión de listado Urbano completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado Urbano: {error}", "error")
        raise RuntimeError(f"Error en impresión Urbano: {error}")
