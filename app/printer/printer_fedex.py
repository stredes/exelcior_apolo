# app/printer/printer_fedex.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import insertar_bloque_firma_ws


def _insertar_firma(path_excel: Path) -> None:
    wb = load_workbook(path_excel)
    ws = wb.active
    insertar_bloque_firma_ws(ws)  # líneas reales en la firma
    wb.save(path_excel)


def print_fedex(file_path, config, df: pd.DataFrame):
    """
    Imprime un listado FedEx:
      - Genera Excel temporal
      - Inserta bloque de firma (líneas reales)
      - Envía a impresora
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de FedEx está vacío y no se puede imprimir.")

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA FEDEX - {fecha_actual}"

        archivo_temporal: Path = generar_excel_temporal(df, titulo, sheet_name="FedEx")
        _insertar_firma(archivo_temporal)

        log_evento(f"📄 Archivo temporal generado para impresión FedEx: {archivo_temporal}", "info")
        enviar_a_impresora(archivo_temporal)
        log_evento("✅ Impresión de listado FedEx completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado FedEx: {error}", "error")
        raise RuntimeError(f"Error en impresión FedEx: {error}")
