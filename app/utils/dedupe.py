import pandas as pd


def drop_duplicates_reference_master(df: pd.DataFrame) -> pd.DataFrame:
    if "reference" in df.columns and "masterTrackingNumber" in df.columns:
        df_copy = df.copy()
        df_copy["__ref__"] = df_copy["reference"].astype(str).str.strip()
        df_copy["__master__"] = df_copy["masterTrackingNumber"].astype(str).str.strip()
        df_dedup = df_copy.drop_duplicates(subset=["__ref__", "__master__"])
        df_dedup.drop(columns=["__ref__", "__master__"], inplace=True)
        return df_dedup.reset_index(drop=True)
    return df


import inspect
import logging
import os
from datetime import datetime
from pathlib import Path


def log_evento(mensaje: str, nivel: str = "info"):
    """
    Guarda logs con nombre dinámico según el archivo donde se llama.
    Ejemplo: logs/etiqueta_editor_log_20250411.log
    """

    # Detectar el nombre del archivo que llama a esta función
    frame = inspect.stack()[1]
    archivo_llamador = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{archivo_llamador}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    # Evitar duplicar handlers
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve())
        for h in logger.handlers
    ):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(nivel.lower(), logger.info)(mensaje)
