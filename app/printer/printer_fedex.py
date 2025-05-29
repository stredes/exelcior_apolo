# M�dulo: printer_fedex.py
# Descripci�n: L�gica de impresi�n correspondiente.

# Módulo: printer_fedex.py
# Descripción: Lógica de impresión para listados FedEx

import pythoncom
from win32com.client import Dispatch
from pathlib import Path
from datetime import datetime
from app.core.logger_eventos import log_evento


def imprimir_fedex(filepath: Path, df):
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        sheet.Cells.EntireColumn.AutoFit()

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = f"FIN DE DÍA FEDEX - {fecha_actual}"

        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = titulo
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # Centrado

        sheet.Range(
            sheet.Cells(2, 1),
            sheet.Cells(df.shape[0] + 2, df.shape[1])
        ).HorizontalAlignment = -4108

        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1

        wb.Save()
        wb.Close(SaveChanges=True)
        log_evento(f"Impresión FedEx completada: {filepath}", "info")

    except Exception as e:
        log_evento(f"Error en impresión FedEx: {e}", "error")
        raise
