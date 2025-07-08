# Módulo: printer_listados.py
# Descripción: Impresión de Listados Generales con formato unificado multiplataforma.

from datetime import datetime
import pandas as pd
from pathlib import Path

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import agregar_nombre_y_firma

def imprimir_listado_general(df: pd.DataFrame):
    """
    Imprime un listado general aplicando título, bordes, centrado y formato en Excel.
    El archivo generado se envía directamente a la impresora predeterminada.
    """
    try:
        if df.empty:
            raise ValueError("El DataFrame del listado general está vacío.")

        fecha = datetime.now().strftime("%d/%m/%Y")
        titulo = f"LISTADO GENERAL - {fecha}"

        df = agregar_nombre_y_firma(df)
        archivo_temporal: Path = generar_excel_temporal(df, titulo, sheet_name="Listado")
        log_evento(f"📄 Archivo temporal generado para Listado General: {archivo_temporal}", "info")

        enviar_a_impresora(archivo_temporal)
        log_evento("✅ Impresión de Listado General completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir Listado General: {error}", "error")
        raise RuntimeError(f"Error en impresión Listado General: {error}")
