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
    guardar_ultimo_path
)

# Aquí puedes mantener o agregar otras utilidades generales no relacionadas con configuración.

import openpyxl

def autoajustar_columnas(workbook):
    """
    Ajusta automáticamente el ancho de las columnas en todas las hojas del workbook.
    """
    for sheet in workbook.worksheets:
        for column_cells in sheet.columns:
            max_length = 0
            column = column_cells[0].column_letter
            for cell in column_cells:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            adjusted_width = max_length + 2
            sheet.column_dimensions[column].width = adjusted_width
