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

    # Selección de engine según extensión
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


def apply_transformation(df: pd.DataFrame, config_columns: dict, mode: str) -> pd.DataFrame:
    if mode == "fedex":
        columns_to_keep = ['shipDate', 'masterTrackingNumber', 'recipientContactName',
                           'recipientCompany', 'recipientCity', 'numberOfPackages']
        df_transformed = df[columns_to_keep].copy()

        rename_dict = {
            'masterTrackingNumber': 'Tracking Number',
            'recipientContactName': 'Cliente',
            'recipientCity': 'Ciudad',
            'numberOfPackages': 'BULTOS'
        }
        df_transformed.rename(columns=rename_dict, inplace=True)
        df_transformed.drop_duplicates(subset=['Tracking Number', 'Cliente', 'Ciudad'], inplace=True)
        df_transformed['BULTOS'] = df_transformed['BULTOS'].fillna(0).astype(int)

        total_bultos = df_transformed['BULTOS'].sum()

        total_row = pd.DataFrame({
            'Tracking Number': [''],
            'Cliente': [''],
            'Ciudad': ['TOTAL BULTOS ='],
            'BULTOS': [total_bultos]
        })

        df_transformed = pd.concat([df_transformed, total_row], ignore_index=True)
        return df_transformed

    # --- Genérico para urbano, listados, etc. ---
    config = config_columns.get(mode, {})
    cols_to_drop = config.get("eliminar", [])
    cols_to_sum = config.get("sumar", [])
    cols_format = config.get("mantener_formato", [])

    df_transformed = df.drop(columns=list(cols_to_drop), errors="ignore").copy()

    # Mantener formato de columnas
    for col in cols_format:
        if col in df_transformed.columns:
            df_transformed[col] = df_transformed[col].astype(str)

    # Calcular sumas
    resumen = {}
    for col in cols_to_sum:
        if col in df_transformed.columns:
            df_transformed[col] = pd.to_numeric(df_transformed[col], errors='coerce')
            resumen[col] = df_transformed[col].sum()

    # Agregar fila resumen si corresponde
    if resumen:
        total_row_data = {col: '' for col in df_transformed.columns}
        for col, total in resumen.items():
            total_row_data[col] = total
        total_row = pd.DataFrame([total_row_data])
        df_transformed = pd.concat([df_transformed, total_row], ignore_index=True)

    return df_transformed
