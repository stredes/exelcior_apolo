import pandas as pd
from pathlib import Path
from typing import Optional
from tkinter import messagebox
from datetime import datetime
import platform
import json

from app.core.logger_eventos import log_evento

# Solo importar estas librerías si estás en Windows
if platform.system() == "Windows":
    import pythoncom
    from win32com.client import Dispatch

CONFIG_PATH = Path("app/config/excel_printer_config.json")

def load_config() -> dict:
    try:
        with CONFIG_PATH.open(encoding='utf-8') as f:
            config = json.load(f)
        log_evento("Configuración cargada correctamente.", "info")
        return config
    except Exception as e:
        log_evento(f"Error al cargar configuración: {e}", "error")
        return {}

def validate_file(file_path: str) -> bool:
    path = Path(file_path)
    if not path.exists():
        messagebox.showerror("Error", "El archivo no existe.")
        log_evento(f"Archivo no encontrado: {file_path}", "error")
        return False
    if path.suffix.lower() not in ('.xlsx', '.xls', '.csv'):
        messagebox.showerror("Error", "Formato de archivo no soportado.")
        log_evento(f"Formato de archivo no soportado: {file_path}", "warning")
        return False
    return True

def load_excel(file_path: str, config: dict, mode: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    path = Path(file_path)
    file_ext = path.suffix.lower()

    engine = {
        ".xlsx": "openpyxl",
        ".xls": "openpyxl",  # Puedes cambiarlo a xlrd si usas .xls
        ".csv": None
    }.get(file_ext)

    skiprows = list(range(config.get(mode, {}).get("start_row", 0)))

    try:
        if engine:
            df = pd.read_excel(path, engine=engine, skiprows=skiprows, nrows=max_rows)
        else:
            df = pd.read_csv(path, skiprows=skiprows, nrows=max_rows)

        df.columns = df.columns.str.strip().str.replace('\u200b', '', regex=True)
        return df
    except Exception as e:
        log_evento(f"Error al leer archivo: {e}", "error")
        raise

def apply_transformation(df: pd.DataFrame, config: dict, mode: str) -> pd.DataFrame:
    log_evento(f"Aplicando transformación para modo: {mode}", "info")

    modo_cfg = config.get(mode, {})
    eliminar = modo_cfg.get("eliminar", [])
    sumar = modo_cfg.get("sumar", [])
    mantener = modo_cfg.get("mantener_formato", [])

    df = df.drop(columns=[col for col in eliminar if col in df.columns], errors='ignore')

    if sumar:
        suma = {col: df[col].sum() if col in df.columns else 0 for col in sumar}
        df = pd.concat([df, pd.DataFrame([suma])], ignore_index=True)

    for col in mantener:
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df

def imprimir_excel(filepath: Path, df: pd.DataFrame, mode: str):
    if platform.system() != "Windows":
        log_evento("Impresión de Excel solo soportada en Windows.", "warning")
        raise NotImplementedError("La impresión desde Excel solo está disponible en Windows.")

    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = {
            "fedex": f"FIN DE DÍA FEDEX - {fecha_actual}",
            "urbano": f"FIN DE DÍA URBANO - {fecha_actual}"
        }.get(mode, f"LISTADO GENERAL - {fecha_actual}")

        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = titulo
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # Centrado

        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1
                cell.HorizontalAlignment = -4108

        wb.Save()
        wb.Close(SaveChanges=True)
        log_evento(f"Impresión completada: {filepath}", "info")
    except Exception as e:
        log_evento(f"Error durante impresión: {e}", "error")
        raise
