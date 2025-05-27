# app/printer/printer.py

import os
import platform
import logging
import inspect
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

try:
    import cups  # type: ignore
except ImportError:
    cups = None


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

        sheet.Cells.EntireColumn.AutoFit()
        sheet.PageSetup.Orientation = 2  # Horizontal
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Cálculo seguro del total según modo
        total = 0
        label = "Items"

        if mode == "fedex":
            if "BULTOS" in df.columns:
                total = df["BULTOS"].sum()
                label = "Piezas"
            else:
                total = len(df)
                label = "Registros"

        elif mode == "urbano":
            if "BULTOS" in df.columns:
                total = df["BULTOS"].sum()
                label = "Piezas"
            else:
                total = len(df)
                label = "Registros"

        elif mode == "listados":
            if "Total" in df.columns:
                total = df["Total"].sum()
                label = "Total $"
            else:
                total = len(df)
                label = "Documentos"

        # Pie de página dinámico con separador de miles
        footer = f'&"Arial,Bold"&8 Impreso: {now}  |  {label}: {total:,.0f}'
        sheet.PageSetup.CenterFooter = footer

        # Asegurar formato de texto para códigos de tracking
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

        sheet.PrintOut()
        wb.Close(SaveChanges=False)
        excel.Quit()

        logging.info(f"Impresión completada: {filepath}")
        messagebox.showinfo("Impresión exitosa", f"Archivo enviado a imprimir:\n{filepath}")

        pythoncom.CoUninitialize()

    except Exception as e:
        logging.error(f"Error al imprimir {filepath}: {e}")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\n{e}")

def log_evento(mensaje: str, nivel: str = "info"):
    frame = inspect.stack()[1]
    caller = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{caller}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve())
               for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    level_fn = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(nivel.lower(), logger.info)
    level_fn(mensaje)
