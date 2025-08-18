# app/utils/utils.py

"""
Módulo de utilidades generales del sistema.
Las funciones de configuración fueron trasladadas a app/config/config_manager.py
para evitar duplicación y mejorar la arquitectura.
"""

# 🔄 Delegación explícita a la fuente única de configuración
from app.config.config_manager import (
    load_config,
    save_config,
    guardar_ultimo_path,
)

from typing import Iterable
import openpyxl


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
    Autoajusta el ancho de columnas de una o varias hojas.

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
        # openpyxl.sheet.columns es un generador de tuplas de celdas por columna
        for column_cells in sheet.columns:
            try:
                # Obtiene la letra de columna de la primera celda de la columna
                first_cell = next(iter(column_cells))
            except StopIteration:
                # Columna vacía (no debería ocurrir), continuar
                continue

            column_letter = getattr(first_cell, "column_letter", None)
            if not column_letter:
                # En casos muy atípicos, podría no existir; saltar
                continue

            max_len = 0
            for cell in column_cells:
                # Evitar fallos por tipos no serializables o muy pesados
                try:
                    value = "" if cell.value is None else str(cell.value)
                    if len(value) > max_len:
                        max_len = len(value)
                except Exception:
                    # No romper por una celda defectuosa
                    continue

            # Ajuste con padding y tope de seguridad
            adjusted = min(max_len + padding, max_width)
            try:
                sheet.column_dimensions[column_letter].width = adjusted
            except Exception:
                # No romper el proceso por un fallo puntual de dimensionado
                continue
