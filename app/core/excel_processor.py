import pandas as pd
import pythoncom
from pathlib import Path
from typing import Optional
from tkinter import messagebox
from win32com.client import Dispatch
from datetime import datetime

from app.core.logger_eventos import log_evento


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
    log_evento(f"Archivo validado correctamente: {file_path}", "info")
    return True


def load_excel(file_path: str, config_columns: dict, mode: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    path_obj = Path(file_path).resolve()
    file_extension = path_obj.suffix.lower()
    file_path_str = path_obj.as_posix()

    if not path_obj.exists():
        msg = f"El archivo no existe en la ruta: {file_path_str}"
        log_evento(msg, "error")
        raise FileNotFoundError(msg)

    if file_extension in [".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"]:
        engine = "openpyxl"
    elif file_extension == ".xlsb":
        engine = "pyxlsb"
    elif file_extension == ".ods":
        engine = "odf"
    elif file_extension in [".csv", ".txt"]:
        engine = None
    else:
        msg = f"Formato de archivo no soportado: {file_extension}"
        log_evento(msg, "warning")
        raise ValueError(msg)

    start_row = config_columns.get(mode, {}).get("start_row", 0)
    skiprows = list(range(start_row)) if start_row > 0 else None

    try:
        if engine:
            df = pd.read_excel(file_path_str, engine=engine, skiprows=skiprows, nrows=max_rows)
        else:
            df = pd.read_csv(file_path_str, skiprows=skiprows, nrows=max_rows)

        df.columns = df.columns.str.strip().str.replace('\u200b', '', regex=True)
        log_evento(f"Columnas leídas: {df.columns.tolist()}", "info")

    except Exception as e:
        log_evento(f"Error al cargar archivo: {e}", "error")
        raise ValueError(f"Error al cargar archivo: {e}")

    if df.empty:
        msg = "El archivo está vacío o no tiene datos válidos"
        log_evento(msg, "warning")
        raise ValueError(msg)

    if 'reference' not in df.columns:
        log_evento("La columna 'reference' no se encontró en el archivo.", "warning")

    log_evento(f"Archivo cargado correctamente: {file_path_str}", "info")
    return df


def apply_transformation(df: pd.DataFrame, config_columns: dict, mode: str) -> pd.DataFrame:
    log_evento(f"Aplicando transformación para modo: {mode}", "info")

    if mode == "fedex":
        columns_to_keep = ['shipDate', 'masterTrackingNumber', 'recipientContactName',
                           'recipientCity', 'numberOfPackages', 'reference']

        missing = [col for col in columns_to_keep if col not in df.columns]
        if missing:
            log_evento(f"Faltan columnas requeridas: {missing}", "error")
            raise KeyError(f"Faltan columnas requeridas: {missing}")

        df_transformed = df[columns_to_keep].copy()

        rename_dict = {
            'shipDate': 'Fecha',
            'masterTrackingNumber': 'Tracking Number',
            'recipientContactName': 'Cliente',
            'recipientCity': 'Ciudad',
            'numberOfPackages': 'BULTOS',
            'reference': 'Referencia'
        }
        df_transformed.rename(columns=rename_dict, inplace=True)
        df_transformed.drop_duplicates(subset=['Tracking Number', 'Cliente', 'Ciudad'], inplace=True)
        df_transformed['BULTOS'] = df_transformed['BULTOS'].fillna(0).astype(int)

        orden = ['Fecha', 'Tracking Number', 'Cliente', 'Ciudad', 'BULTOS', 'Referencia']
        df_transformed = df_transformed[orden]

        log_evento(f"Transformación para 'fedex' completada. Total filas: {len(df_transformed)}", "info")
        return df_transformed

    # Otros modos...
    return df


def imprimir_excel(filepath: Path, df: pd.DataFrame, mode: str):
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        # Ajustar columnas y preparar título
        sheet.Cells.EntireColumn.AutoFit()

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = {
            "fedex": f"FIN DE DÍA FEDEX - {fecha_actual}",
            "urbano": f"FIN DE DÍA URBANO - {fecha_actual}"
        }.get(mode.lower(), f"LISTADO GENERAL - {fecha_actual}")

        # Insertar título
        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = titulo
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # Centrado

        # Centrar contenido de tabla
        sheet.Range(
            sheet.Cells(2, 1),
            sheet.Cells(df.shape[0] + 2, df.shape[1])
        ).HorizontalAlignment = -4108  # xlCenter

        # Cuadriculado con bordes
        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1  # xlContinuous

        wb.Save()
        wb.Close(SaveChanges=True)
        log_evento(f"Impresión completada correctamente: {filepath}", "info")

    except Exception as e:
        log_evento(f"Error durante impresión: {e}", "error")
        raise RuntimeError(f"Error durante impresión: {e}")
