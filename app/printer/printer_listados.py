# app/printer/printer_listados.py

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from openpyxl import load_workbook

from app.core.logger_eventos import log_evento
from app.core.impression_tools import generar_excel_temporal, enviar_a_impresora

__all__ = ["print_listados"]


def _aplicar_footer_listados(path_excel: Path, filas: int) -> None:
    """Aplica pie de página con conteo de filas y fecha/hora."""
    wb = load_workbook(path_excel)
    ws = wb.active

    # Texto footer (respetado por LibreOffice/Excel)
    # Izquierda: filas; Derecha: fecha/hora
    ws.oddFooter.left.text = f"Filas: {filas}"
    ws.oddFooter.right.text = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Usar el mismo para todas las páginas
    ws.evenFooter.left.text = ws.oddFooter.left.text
    ws.evenFooter.right.text = ws.oddFooter.right.text

    wb.save(path_excel)


def print_listados(file_path: Optional[Path], config: dict, df: pd.DataFrame) -> None:
    """
    Imprime un listado general con:
      - Título
      - Footer con conteo de filas y timestamp
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de Listado está vacío y no se puede imprimir.")

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"LISTADO GENERAL - {fecha_actual}"

        xlsx_tmp: Path = generar_excel_temporal(df, titulo, sheet_name="Listado")
        log_evento(f"📄 Archivo temporal generado para impresión Listado General: {xlsx_tmp}", "info")

        _aplicar_footer_listados(xlsx_tmp, len(df.index))

        enviar_a_impresora(xlsx_tmp)
        log_evento("✅ Impresión de listado general completada correctamente.", "info")

    except Exception as error:
        log_evento(f"❌ Error al imprimir listado general: {error}", "error")
        raise RuntimeError(f"Error en impresión Listado General: {error}")
