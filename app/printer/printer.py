from pathlib import Path
from datetime import datetime
from tkinter import messagebox
import pandas as pd
import logging

try:
    import pythoncom
    from win32com.client import Dispatch
except ImportError:
    Dispatch = None
    pythoncom = None


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

        # Ajuste de columnas
        sheet.Cells.EntireColumn.AutoFit()

        # Configuración de impresión
        sheet.PageSetup.Orientation = 2  # Horizontal
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Título y totales
        if mode == "fedex":
            bultos_col = next((col for col in df.columns if col.strip().lower() == "bultos"), None)
            total = df[bultos_col].sum() if bultos_col else len(df)
            label = "Piezas"
            titulo = "FIN DE DÍA FEDEX"
        elif mode == "urbano":
            piezas_col = next((col for col in df.columns if col.strip().lower() == "piezas"), None)
            total = df[piezas_col].sum() if piezas_col else 0
            label = "Bultos"
            titulo = "FIN DE DÍA URBANO"
        else:
            total = len(df)
            label = "Items"
            titulo = "LISTADO GENERAL"

        # Encabezado
        sheet.PageSetup.CenterHeader = f"&\"Arial,Bold\"&14 {titulo}"

        # Pie de página con firma
        sheet.PageSetup.LeftFooter = "&\"Arial\"&10 ---------------------------\nFirma"
        sheet.PageSetup.CenterFooter = f"&\"Arial,Bold\"&8 Impreso el: {now}  |  Total {label}: {total}"

        # Formato de tabla
        used_range = sheet.UsedRange
        rows = used_range.Rows.Count
        cols = used_range.Columns.Count

        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                cell = sheet.Cells(r, c)
                cell.HorizontalAlignment = -4108  # xlCenter
                cell.VerticalAlignment = -4108    # xlCenter
                cell.Borders.Weight = 2           # xlThin

        for c in range(1, cols + 1):
            header = str(sheet.Cells(1, c).Value).strip().lower()
            if "pieza" in header or "bulto" in header:
                sheet.Columns(c).ColumnWidth = 10
            elif "rastreo" in header or "tracking" in header:
                sheet.Columns(c).ColumnWidth = 18
            else:
                sheet.Columns(c).AutoFit()

        # Tracking Number como texto
        if (
            mode == "fedex"
            and config_columns.get(mode, {}).get("mantener_formato")
            and "Tracking Number" in df.columns
        ):
            col_idx = df.columns.get_loc("Tracking Number") + 1
            sheet.Columns(col_idx).NumberFormat = "@"
            for row in range(2, rows + 1):
                cell = sheet.Cells(row, col_idx)
                val = cell.Value
                if val is not None:
                    try:
                        cell.Value = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                    except Exception:
                        cell.Value = str(cell.Value)

        # Imprimir
        sheet.PrintOut()
        wb.Close(SaveChanges=False)
        excel.Quit()

        logging.info(f"Impresión completada: {filepath}")
        messagebox.showinfo("Impresión exitosa", f"Archivo enviado a imprimir:\n{filepath}")

        pythoncom.CoUninitialize()

    except Exception as e:
        logging.error(f"Error al imprimir {filepath}: {e}")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\n{e}")
