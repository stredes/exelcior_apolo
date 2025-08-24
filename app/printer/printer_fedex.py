# app/printer/printer_fedex.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import (
    prepare_fedex_dataframe,
    insertar_bloque_firma_ws,
    agregar_footer_info_ws,
    formatear_tabla_ws,
)

def print_fedex(file_path, config, df: pd.DataFrame):
    """
    Genera un informe FedEx profesional:
      - Dedup por Tracking Number (prioridad: master > piece > tracking)
      - Columnas: Tracking Number | Fecha | Referencia | Ciudad | Receptor | BULTOS
      - Total de piezas en el pie + timestamp
      - Bloque de firma con líneas
      - Encabezados, bordes y anchos mínimos para lectura clara
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de FedEx está vacío y no se puede imprimir.")

        # 1) Preparar datos (limpieza / shaping / dedup)
        df_out, id_col, total_piezas = prepare_fedex_dataframe(df)
        if df_out.empty:
            raise ValueError("No hay filas válidas tras eliminar duplicados por Tracking Number.")

        filas = len(df_out)
        if id_col:
            log_evento(
                f"[FedEx] Columna tracking usada: '{id_col}'. Filas tras dedup: {filas}. Total piezas: {total_piezas}.",
                "info"
            )
        else:
            log_evento(
                f"[FedEx] No se detectó columna de tracking válida. Filas tras limpieza: {filas}.",
                "warning"
            )

        # 2) Título
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA FEDEX - {fecha_actual}"

        # 3) Excel temporal base
        tmp_path: Path = generar_excel_temporal(df_out, titulo, sheet_name="FedEx")
        log_evento(f"📄 Archivo temporal generado para impresión FedEx: {tmp_path}", "info")

        # 4) Post-procesar con openpyxl: formato + firma + footer
        wb = load_workbook(tmp_path)
        try:
            ws = wb.active
            formatear_tabla_ws(ws)                  # estilo profesional (bordes/anchos/encabezados)
            insertar_bloque_firma_ws(ws)            # líneas de firma (Nombre/Firma)
            agregar_footer_info_ws(ws, total_piezas)  # fecha/hora + total piezas
            wb.save(tmp_path)
        finally:
            wb.close()

        # 5) Imprimir (permite config de impresora si está definida)
        printer_name = (config or {}).get("printer_name")
        enviar_a_impresora(tmp_path, printer_name=printer_name)

        log_evento("✅ Impresión de listado FedEx completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado FedEx: {error}", "error")
        raise RuntimeError(f"Error en impresión FedEx: {error}")
