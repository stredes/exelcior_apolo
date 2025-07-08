# Módulo: printer_urbano.py
# Descripción: Impresión de listados Urbano con formato unificado y soporte multiplataforma.

from datetime import datetime
import pandas as pd
from pathlib import Path

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora
from app.printer.printer_tools import agregar_nombre_y_firma

def imprimir_urbano(df: pd.DataFrame):
    """
    Imprime un listado Urbano con título, formato de celdas, bordes y centrado.
    Se genera un archivo Excel temporal estilizado y se envía automáticamente a impresión.
    """
    try:
        if df.empty:
            raise ValueError("El DataFrame de Urbano está vacío y no se puede imprimir.")

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA URBANO - {fecha_actual}"

        df = agregar_nombre_y_firma(df)
        archivo_temporal: Path = generar_excel_temporal(df, titulo, sheet_name="Urbano")
        log_evento(f"📄 Archivo temporal generado para impresión Urbano: {archivo_temporal}", "info")

        enviar_a_impresora(archivo_temporal)
        log_evento("✅ Impresión de listado Urbano completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado Urbano: {error}", "error")
        raise RuntimeError(f"Error en impresión Urbano: {error}")
