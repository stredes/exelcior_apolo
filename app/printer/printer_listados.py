# app/printer/printer_listados.py

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora

__all__ = ["print_listados"]  # facilita introspección/registro por nombre


def print_listados(file_path: Optional[Path], config: dict, df: pd.DataFrame) -> None:
    """
    Imprime un listado general (modo 'listados') con encabezado y formato.

    Parámetros
    ----------
    file_path : Path | None
        No se usa en este flujo; se mantiene por compatibilidad con el dispatcher.
    config : dict
        Configuración del modo (no requerida aquí).
    df : pd.DataFrame
        DataFrame ya transformado que se imprimirá.
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de Listado está vacío y no se puede imprimir.")

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"LISTADO GENERAL - {fecha_actual}"

        xlsx_tmp: Path = generar_excel_temporal(df, titulo, sheet_name="Listado")
        log_evento(f"📄 Archivo temporal generado para impresión Listado General: {xlsx_tmp}", "info")

        enviar_a_impresora(xlsx_tmp)
        log_evento("✅ Impresión de listado general completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado general: {error}", "error")
        # Reelevar con mensaje claro para la UI
        raise RuntimeError(f"Error en impresión Listado General: {error}")
