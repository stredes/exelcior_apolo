# Módulo: printer_fedex.py
# Descripción: Impresión de listados FedEx con formato unificado y soporte multiplataforma.

from datetime import datetime
import pandas as pd
from pathlib import Path

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora


def imprimir_fedex(df: pd.DataFrame):
    """
    Imprime un listado FedEx con título, formato de celdas, bordes y centrado.
    Se genera un archivo Excel temporal estilizado y se envía automáticamente a impresión.
    """
    try:
        if df.empty:
            raise ValueError("El DataFrame de FedEx está vacío y no se puede imprimir.")

        # Generar título dinámico con la fecha actual
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA FEDEX - {fecha_actual}"

        # Generar archivo Excel temporal con formato
        archivo_temporal: Path = generar_excel_temporal(df, titulo, sheet_name="FedEx")

        log_evento(f"📄 Archivo temporal generado para impresión FedEx: {archivo_temporal}", "info")

        # Enviar archivo generado a la impresora
        enviar_a_impresora(archivo_temporal)

        log_evento("✅ Impresión de listado FedEx completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado FedEx: {error}", "error")
        raise RuntimeError(f"Error en impresión FedEx: {error}")
