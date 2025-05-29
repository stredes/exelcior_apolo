# M�dulo: printer_listados.py
# Descripci�n: L�gica de impresi�n correspondiente.

# Módulo: printer_listados.py
# Descripción: Lógica de impresión para Listados Generales

import pythoncom
from win32com.client import Dispatch
from pathlib import Path
from datetime import datetime
from app.core.logger_eventos import log_evento


def imprimir_listado_general(filepath: Path, df):
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        # Autoajuste de columnas
        sheet.Cells.EntireColumn.AutoFit()

        # Título genérico con fecha
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"LISTADO GENERAL - {fecha_actual}"

        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = titulo
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108

        # Centrar contenido
        sheet.Range(
            sheet.Cells(2, 1),
            sheet.Cells(df.shape[0] + 2, df.shape[1])
        ).HorizontalAlignment = -4108

        # Cuadriculado
        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1

        wb.Save()
        wb.Close(SaveChanges=True)
        log_evento(f"Impresión Listado General completada: {filepath}", "info")

    except Exception as e:
        log_evento(f"Error en impresión Listado General: {e}", "error")
        raise
