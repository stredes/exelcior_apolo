import pandas as pd
from pathlib import Path
from typing import Optional
from tkinter import messagebox

def validate_file(file_path: str) -> bool:
    path = Path(file_path)
    if not path.exists():
        messagebox.showerror("Error", "El archivo no existe.")
        return False
    if path.suffix.lower() not in ('.xlsx', '.xls'):
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

    # 👇 Aquí se toma correctamente el valor de start_row del config
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

    # --- Otros modos ---
    cols_to_drop = config_columns.get(mode, {}).get("eliminar", set())
    return df.drop(columns=list(cols_to_drop), errors="ignore").copy()
