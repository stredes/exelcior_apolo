import pandas as pd
from pathlib import Path
from tempfile import NamedTemporaryFile
import platform
import os

from app.utils.utils import autoajustar_columnas
from app.core.logger_eventos import log_evento

def generar_excel_temporal(df: pd.DataFrame, titulo: str, sheet_name: str = "Listado") -> Path:
    """
    Genera un archivo Excel temporal con título y formato adecuado.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Side, Font

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Insertar título
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
    celda_titulo = ws.cell(row=1, column=1)
    celda_titulo.value = titulo
    celda_titulo.font = Font(bold=True, size=14)
    celda_titulo.alignment = Alignment(horizontal="center")

    # Encabezados
    for idx, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=2, column=idx, value=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Datos
    for r_idx, row in enumerate(df.itertuples(index=False), start=3):
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(horizontal="center")

    # Bordes finos
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))

    for row in ws.iter_rows(min_row=2, max_row=2 + len(df), min_col=1, max_col=len(df.columns)):
        for cell in row:
            cell.border = thin_border

    # Autoajuste de columnas
    autoajustar_columnas(ws)

    # Guardar archivo temporal
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        wb.save(tmp.name)
        return Path(tmp.name)

def enviar_a_impresora(archivo: Path):
    """
    Envía un archivo Excel a la impresora predeterminada, compatible con Windows y Linux.
    """
    try:
        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(str(archivo), "print")
        elif sistema == "Linux":
            os.system(f"lp '{archivo}'")
        else:
            raise OSError(f"Sistema no soportado para impresión: {sistema}")
    except Exception as e:
        log_evento(f"Error al enviar a impresora: {e}", "error")
        raise
