# app/utils/utils.py
# -*- coding: utf-8 -*-
"""
Módulo de utilidades generales del sistema.

Las funciones de configuración fueron trasladadas a app/config/config_manager.py
para evitar duplicación y mejorar la arquitectura.

Este módulo expone un alias de compatibilidad `load_config_from_file()`
para código legado que aún lo importa desde aquí.
"""

from typing import Iterable
import openpyxl

# 🔄 Delegación explícita a la fuente única de configuración
from app.config.config_manager import (
    load_config,
    save_config,
    guardar_ultimo_path,
)

__all__ = [
    "load_config",
    "save_config",
    "guardar_ultimo_path",
    "autoajustar_columnas",
    "load_config_from_file",  # alias de compatibilidad
]


def _iter_worksheets(libro_o_hoja) -> Iterable[openpyxl.worksheet.worksheet.Worksheet]:
    """
    Normaliza la entrada para iterar hojas.
    - Si recibe un Workbook (tiene .worksheets), devuelve sus hojas.
    - Si recibe una Worksheet, la envuelve en una lista.
    """
    if hasattr(libro_o_hoja, "worksheets"):  # Workbook
        return libro_o_hoja.worksheets
    return [libro_o_hoja]  # Worksheet


def autoajustar_columnas(libro_o_hoja, max_width: int = 60, padding: int = 2) -> None:
    """
    Autoajusta el ancho de columnas de una o varias hojas (openpyxl).

    Acepta:
      - openpyxl.Workbook (ajusta todas sus hojas)
      - openpyxl.Worksheet (ajusta solo esa hoja)

    Parámetros:
      max_width: ancho máximo de columna para evitar desbordes visuales.
      padding:  relleno adicional de caracteres para que respire el contenido.

    Notas:
      - Ignora celdas None y maneja excepciones silenciosamente.
      - Si una columna no tiene celdas con valor, mantiene el ancho por defecto.
    """
    for sheet in _iter_worksheets(libro_o_hoja):
        # openpyxl.Worksheet.columns es un generador de tuplas de celdas por columna
        for column_cells in sheet.columns:
            try:
                # Primera celda de la columna para obtener la letra
                first_cell = next(iter(column_cells))
            except StopIteration:
                # Columna vacía
                continue

            column_letter = getattr(first_cell, "column_letter", None)
            if not column_letter:
                # Caso atípico: sin letra de columna
                continue

            max_len = 0
            for cell in column_cells:
                try:
                    value = "" if cell.value is None else str(cell.value)
                    if len(value) > max_len:
                        max_len = len(value)
                except Exception:
                    # No romper por una celda problemática
                    continue

            # Ajuste con padding y tope de seguridad
            adjusted = min(max_len + padding, max_width)
            try:
                sheet.column_dimensions[column_letter].width = adjusted
            except Exception:
                # No romper por un fallo puntual de dimensionado
                continue


# --- Compatibilidad con código existente ---
def load_config_from_file():
    """
    Alias de compatibilidad para el código que aún importa
    'load_config_from_file' desde app.utils.utils.
    Internamente delega en app.config.config_manager.load_config().
    """
    return load_config()
