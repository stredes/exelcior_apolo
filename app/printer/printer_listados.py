from datetime import datetime
import pandas as pd
from pathlib import Path

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora


def print_listados(file_path, config, df: pd.DataFrame):
    """
    Imprime un listado general (modo 'listados') con encabezado y formato.
    """
    try:
        if df.empty:
            raise ValueError("El DataFrame de Listado está vacío y no se puede imprimir.")

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"LISTADO GENERAL - {fecha_actual}"

        archivo_temporal: Path = generar_excel_temporal(df, titulo, sheet_name="Listado")
        log_evento(f"📄 Archivo temporal generado para impresión Listado General: {archivo_temporal}", "info")

        enviar_a_impresora(archivo_temporal)
        log_evento("✅ Impresión de listado general completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado general: {error}", "error")
        raise RuntimeError(f"Error en impresión Listado General: {error}")
