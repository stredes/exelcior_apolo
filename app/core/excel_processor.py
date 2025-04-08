import pandas as pd
from pathlib import Path
from typing import Optional
from tkinter import messagebox
from app.core.logger_bod1 import capturar_log_bod1  # ✅ Correcto

def validate_file(file_path: str) -> bool:
    path = Path(file_path)
    if not path.exists():
        messagebox.showerror("Error", "El archivo no existe.")
        return False
    if path.suffix.lower() not in ('.xlsx', '.xls', '.csv'):
        messagebox.showerror("Error", "Formato de archivo no soportado.")
        return False
    return True

def load_excel(file_path: str, config_columns: dict, mode: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    path_obj = Path(file_path).resolve()
    file_extension = path_obj.suffix.lower()
    file_path_str = path_obj.as_posix()

    if not path_obj.exists():
        raise FileNotFoundError(f"El archivo no existe en la ruta: {file_path_str}")

    if file_extension in [".xlsx", ".xlsm", ".xltx", ".xltm"]:
        engine = "openpyxl"
    elif file_extension == ".xls":
        engine = "openpyxl"
    elif file_extension == ".xlsb":
        engine = "pyxlsb"
    elif file_extension == ".ods":
        engine = "odf"
    elif file_extension in [".csv", ".txt"]:
        engine = None
    else:
        raise ValueError(f"Formato de archivo no soportado: {file_extension}")

    start_row = config_columns.get(mode, {}).get("start_row", 0)
    skiprows = list(range(start_row)) if start_row > 0 else None

    try:
        if engine:
            df = pd.read_excel(file_path_str, engine=engine, skiprows=skiprows, nrows=max_rows)
        else:
            df = pd.read_csv(file_path_str, skiprows=skiprows, nrows=max_rows)
    except Exception as e:
        raise ValueError(f"Error al cargar archivo: {e}")

    if df.empty:
        raise ValueError("El archivo está vacío o no tiene datos válidos")

    return df

def apply_transformation(df: pd.DataFrame, config_columns: dict, mode: str):
    if mode == "fedex":
        columns_needed = ['shipDate', 'masterTrackingNumber', 'reference', 'recipientCity', 'pieceTrackingNumber']
        df_fedex = df[columns_needed].copy()
        df_fedex = df_fedex[df_fedex['masterTrackingNumber'].notna()]

        grouped = df_fedex.groupby('masterTrackingNumber').agg({
            'shipDate': 'first',
            'reference': 'first',
            'recipientCity': 'first',
            'pieceTrackingNumber': 'count'
        }).reset_index()

        grouped.columns = ['Tracking Number', 'Fecha', 'Referencia', 'Ciudad', 'BULTOS']
        total_bultos = grouped['BULTOS'].sum()

        return grouped, total_bultos

    # --- Genérico para urbano, listados, etc. ---
    config = config_columns.get(mode, {})
    cols_to_drop = config.get("eliminar", [])
    cols_to_sum = config.get("sumar", [])
    cols_format = config.get("mantener_formato", [])

    df_transformed = df.drop(columns=list(cols_to_drop), errors="ignore").copy()

    for col in cols_format:
        if col in df_transformed.columns:
            df_transformed[col] = df_transformed[col].astype(str)

    resumen = {}
    for col in cols_to_sum:
        if col in df_transformed.columns:
            df_transformed[col] = pd.to_numeric(df_transformed[col], errors='coerce')
            resumen[col] = df_transformed[col].sum()

    # ✅ En lugar de agregar fila, devolver el resumen por separado
    total = None
    if resumen:
        total = list(resumen.values())[0]  # asumimos un solo campo a sumar

    return df_transformed, total
