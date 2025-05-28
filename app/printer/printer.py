import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from tkinter import messagebox

try:
    import pythoncom  # type: ignore
    from win32com.client import Dispatch  # type: ignore
except ImportError:
    pythoncom = None
    Dispatch = None

from app.core.logger_eventos import log_evento  # ✅ uso centralizado


def print_document(filepath: Path, mode: str, config_columns: dict, df: pd.DataFrame):
    try:
        if Dispatch is None or pythoncom is None:
            raise EnvironmentError("win32com.client o pythoncom no disponible. Instala pywin32.")

        pythoncom.CoInitialize()

        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        # Estética general
        sheet.Cells.EntireColumn.AutoFit()
        sheet.PageSetup.Orientation = 2  # Horizontal
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # ----------- TITULO DINÁMICO -----------------
        titulo = {
            "fedex": f"FIN DE DÍA FEDEX - {now}",
            "urbano": f"FIN DE DÍA URBANO - {now}"
        }.get(mode.lower(), f"LISTADO GENERAL - {now}")

        # Insertar fila superior y escribir título centrado
        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = titulo
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # xlCenter

        # ----------- PIE DE PÁGINA ------------------
        total = 0
        label = "Items"

        if mode in ["fedex", "urbano"] and "BULTOS" in df.columns:
            total = df["BULTOS"].sum()
            label = "Piezas"
        elif "Total" in df.columns:
            total = df["Total"].sum()
            label = "Total $"
        else:
            total = len(df)
            label = "Registros"

        footer = f'&"Arial,Bold"&8 Impreso: {now}  |  {label}: {total:,.0f}'
        sheet.PageSetup.CenterFooter = footer

        # ----------- FORMATO TRACKING COMO TEXTO --------
        if mode == "fedex" and "Tracking Number" in df.columns:
            col_idx = list(df.columns).index("Tracking Number") + 1
            sheet.Columns(col_idx).NumberFormat = "@"
            for row in range(2, sheet.UsedRange.Rows.Count + 1):
                val = sheet.Cells(row, col_idx).Value
                if val is not None:
                    try:
                        sheet.Cells(row, col_idx).Value = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                    except Exception:
                        pass

        # ----------- CENTRAR TODO EL CONTENIDO ------------
        sheet.Range(
            sheet.Cells(2, 1),
            sheet.Cells(df.shape[0] + 2, df.shape[1])
        ).HorizontalAlignment = -4108  # xlCenter

        # ----------- APLICAR BORDES A TODA LA TABLA -------
        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1  # xlContinuous

        # ----------- IMPRIMIR Y CERRAR --------------------
        sheet.PrintOut()
        wb.Close(SaveChanges=False)
        excel.Quit()

        log_evento(f"Impresión completada: {filepath}", "info")
        messagebox.showinfo("Impresión exitosa", f"Archivo enviado a imprimir:\n{filepath}")
        pythoncom.CoUninitialize()

    except Exception as e:
        log_evento(f"Error al imprimir {filepath}: {e}", "error")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\n{e}")
