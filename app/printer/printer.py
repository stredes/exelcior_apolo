import os
import logging
import pythoncom
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
from win32com.client import Dispatch
import inspect
from app.printer.print_router import print_document


def print_document(filepath: Path, mode: str, config_columns: dict, df):
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        sheet.Cells.EntireColumn.AutoFit()

        title = {
            "fedex": "FIN DÍA FEDEX",
            "urbano": "FIN DÍA URBANO"
        }.get(mode.lower(), "LISTADO GENERAL")

        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = title
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 14
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # Centrado

        if mode.lower() in ["fedex", "urbano"]:
            used_rows = sheet.UsedRange.Rows.Count
            sheet.Cells(used_rows + 2, 1).Value = "Recibe: ______________"
            sheet.Cells(used_rows + 3, 1).Value = "Firma: __________________________"
            sheet.Range(sheet.Cells(used_rows + 2, 1), sheet.Cells(used_rows + 3, 1)).Font.Size = 10

        sheet.PageSetup.Orientation = 2
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Pie de página dinámico y seguro
        label = "Registros"
        if mode == "fedex":
            total = df["BULTOS"].sum() if "BULTOS" in df.columns else len(df)
            label = "Piezas"
        elif mode == "urbano":
            total = df["BULTOS"].sum() if "BULTOS" in df.columns else len(df)
            label = "Bultos"
        elif mode == "listados":
            total = len(df)
            label = "Documentos"
        else:
            total = len(df)

        sheet.PageSetup.CenterFooter = f"&\"Arial,Bold\"&8 Impreso el: {now} | Total {label}: {total:,}"


        sheet.PrintOut()
        wb.Close(SaveChanges=False)
        excel.Quit()

        log_evento(f"Archivo enviado a imprimir: {filepath.name}", "info")
        messagebox.showinfo("Impresión exitosa", f"Archivo enviado a imprimir:\\n{filepath}")

        pythoncom.CoUninitialize()

    except Exception as e:
        logging.error(f"Error al imprimir {filepath}: {e}")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\\n{e}")

def log_evento(mensaje: str, nivel: str = "info"):
    frame = inspect.stack()[1]
    caller = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{caller}_log_{datetime.now().strftime('%Y%m%d')}"
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    getattr(logger, nivel.lower(), logger.info)(mensaje)