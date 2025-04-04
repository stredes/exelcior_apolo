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

        # Ajuste automático de columnas
        sheet.Cells.EntireColumn.AutoFit()

        # Configuración de impresión
        sheet.PageSetup.Orientation = 2  # Horizontal
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        # Fecha y hora actual
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # --- Contador dinámico según el modo ---
        if mode == "fedex":
            bultos_col = next((col for col in df.columns if col.strip().lower() == "bultos"), None)
            total = df[bultos_col].sum() if bultos_col else len(df)
            label = "Piezas"
        elif mode == "urbano":
            piezas_col = next((col for col in df.columns if col.strip().lower() == "piezas"), None)
            total = df[piezas_col].sum() if piezas_col else 0
            label = "Bultos"
        else:
            total = len(df)
            label = "Items"

        # Establecer pie de página
        sheet.PageSetup.CenterFooter = f"&\"Arial,Bold\"&8 Impreso el: {now}  |  Total {label}: {total}"

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
                val = cell.Value
                if val is not None:
                    try:
                        cell.Value = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                    except Exception:
                        cell.Value = str(cell.Value)

        # Enviar a imprimir
        sheet.PrintOut()
        wb.Close(SaveChanges=False)
        excel.Quit()

        logging.info(f"Impresión completada: {filepath}")
        messagebox.showinfo("Impresión exitosa", f"Archivo enviado a imprimir:\n{filepath}")

        pythoncom.CoUninitialize()

    except Exception as e:
        logging.error(f"Error al imprimir {filepath}: {e}")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\n{e}")
