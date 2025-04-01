from pathlib import Path
from datetime import datetime
from tkinter import messagebox
import pandas as pd
import logging
import time

try:
    from win32com.client import Dispatch
except ImportError:
    Dispatch = None


def print_document(filepath: Path, mode: str, config_columns: dict, df: pd.DataFrame):
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        if Dispatch is None:
            raise EnvironmentError("win32com.client no disponible. Instala pywin32.")

        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        # Ajuste automático de columnas
        sheet.Cells.EntireColumn.AutoFit()

        # Configuración de impresión
        sheet.PageSetup.Orientation = 2  # Horizontal
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        # Pie de página
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.PageSetup.CenterFooter = f"&\"Arial,Bold\"&8 Impreso el: {now}"

        # Formato especial para FedEx si corresponde
        if (
            mode == "fedex"
            and config_columns.get(mode, {}).get("mantener_formato")
            and "Tracking Number" in df.columns
        ):
            col_idx = list(df.columns).index("Tracking Number") + 1
            sheet.Columns(col_idx).NumberFormat = "@"
            used_rows = sheet.UsedRange.Rows.Count

            for row in range(2, used_rows + 1):
                cell = sheet.Cells(row, col_idx)
                if cell.Value is not None:
                    try:
                        val = cell.Value
                        if isinstance(val, float) and val.is_integer():
                            cell.Value = str(int(val))
                        else:
                            cell.Value = str(val)
                    except Exception:
                        cell.Value = str(cell.Value)

        # Imprimir
        sheet.PrintOut()
        wb.Close(SaveChanges=False)
        excel.Quit()

        logging.info(f"Impresión completada: {filepath}")
        messagebox.showinfo("Impresión exitosa", f"Archivo enviado a imprimir:\n{filepath}")

    except Exception as e:
        logging.error(f"Error al imprimir {filepath}: {e}")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\n{e}")
