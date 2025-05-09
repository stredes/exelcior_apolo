# app/core/excel_processor.py

from pathlib import Path
from tkinter import messagebox
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from app.utils.logger_setup import log_evento


def validate_file(file_path: str) -> bool:
    path = Path(file_path)
    if not path.exists():
        messagebox.showerror("Error", "El archivo no existe.")
        log_evento(f"Archivo no encontrado: {file_path}", "error")
        return False
    if path.suffix.lower() not in (
        ".xlsx",
        ".xls",
        ".csv",
        ".xlsm",
        ".xlsb",
        ".ods",
        ".txt",
    ):
        messagebox.showerror("Error", "Formato de archivo no soportado.")
        log_evento(f"Formato no soportado: {file_path}", "error")
        return False
    return True


def load_excel(
    file_path: str,
    config_columns: Dict[str, Any],
    mode: str,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Carga un archivo Excel/CSV aplicando skiprows según config_columns[mode]['start_row'].
    """
    if not validate_file(file_path):
        raise FileNotFoundError(f"Validación fallida para: {file_path}")

    path_obj = Path(file_path).resolve()
    ext = path_obj.suffix.lower()
    log_evento(f"Cargando archivo: {file_path}", "info")

    # Selección de engine
    if ext in [".xlsx", ".xlsm", ".xltx", ".xltm"]:
        engine = "openpyxl"
    elif ext == ".xls":
        engine = "xlrd"
    elif ext == ".xlsb":
        engine = "pyxlsb"
    elif ext == ".ods":
        engine = "odf"
    elif ext in [".csv", ".txt"]:
        engine = None
    else:
        log_evento(f"Formato no soportado: {ext}", "error")
        raise ValueError(f"Formato no soportado: {ext}")

    # Determinar start_row
    start_row = 0
    if mode in config_columns and isinstance(config_columns[mode], dict):
        start_row = config_columns[mode].get("start_row", 0)
    skiprows = list(range(start_row)) if start_row > 0 else None

    try:
        if engine:
            df = pd.read_excel(
                path_obj, engine=engine, skiprows=skiprows, nrows=max_rows
            )
        else:
            df = pd.read_csv(path_obj, skiprows=skiprows, nrows=max_rows)
    except Exception as e:
        log_evento(f"Error al leer archivo: {e}", "error")
        raise ValueError(f"No se pudo leer el archivo: {e}")

    if df.empty:
        log_evento("Archivo cargado pero vacío", "warning")
        raise ValueError("El archivo está vacío o no tiene datos")

    log_evento("Archivo cargado correctamente", "info")
    return df


def apply_transformation(
    df: pd.DataFrame, config_columns: Dict[str, Any], mode: str
) -> Tuple[pd.DataFrame, Optional[float]]:
    """
    Transforma el DataFrame según el modo:
      - 'fedex' devuelve (grouped_df, total_bultos)
      - otros modos: (df_transformed, total_sum) donde total_sum es la suma de la primera columna de 'sumar'
    """
    log_evento(f"Transformando modo: {mode}", "info")

    # Modo FedEx especial
    if mode == "fedex":
        cols = [
            "shipDate",
            "masterTrackingNumber",
            "reference",
            "recipientCity",
            "recipientContactName",
            "pieceTrackingNumber",
        ]
        df_f = df.copy()
        missing = [c for c in cols if c not in df_f.columns]
        if missing:
            log_evento(f"Columnas faltantes FedEx: {missing}", "error")
            raise KeyError(f"Faltan columnas para FedEx: {missing}")

        df_f = df_f[df_f["masterTrackingNumber"].notna()]
        grouped = (
            df_f.groupby("masterTrackingNumber")
            .agg(
                {
                    "shipDate": "first",
                    "reference": "first",
                    "recipientCity": "first",
                    "recipientContactName": "first",
                    "pieceTrackingNumber": "count",
                }
            )
            .reset_index()
        )
        grouped.columns = [
            "Tracking Number",
            "Fecha",
            "Referencia",
            "Ciudad",
            "Receptor",
            "BULTOS",
        ]
        total_bultos = grouped["BULTOS"].sum()
        log_evento(f"FedEx: {len(grouped)} registros, {total_bultos} bultos", "info")
        return grouped, float(total_bultos)

    # Modo genérico
    cfg = config_columns.get(mode, {})
    eliminar = cfg.get("eliminar", [])
    sumar = cfg.get("sumar", [])
    formato = cfg.get("mantener_formato", [])

    df_t = df.drop(columns=eliminar, errors="ignore").copy()
    # Conservar formato
    for col in formato:
        if col in df_t.columns:
            df_t[col] = df_t[col].astype(str)

    # Sumar columnas
    resumen = {}
    for col in sumar:
        if col in df_t.columns:
            df_t[col] = pd.to_numeric(df_t[col], errors="coerce")
            resumen[col] = df_t[col].sum()

    total = None
    if resumen:
        # toma la primera suma como total
        total = float(next(iter(resumen.values())))
    log_evento(f"Modo {mode} completado. Total: {total}", "info")
    return df_t, total
