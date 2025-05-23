import json
from pathlib import Path

import pandas as pd
from app.core.logger_bod1 import capturar_log_bod1

# Ruta del archivo de configuración
CONFIG_FILE = Path("excel_printer_config.json")


# ---------- Cargar Configuración ----------
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                capturar_log_bod1("Configuración cargada correctamente", nivel="info")
                return config
        except Exception as e:
            capturar_log_bod1(f"Error al cargar configuración: {e}", nivel="error")
            return {}
    else:
        capturar_log_bod1(
            "Archivo de configuración no encontrado. Se cargará configuración vacía",
            nivel="warning",
        )
        return {}


# ---------- Guardar Configuración ----------
def save_config(config_data):
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        return obj

    try:
        serializable_data = convert_sets(config_data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=4)
        capturar_log_bod1("Configuración guardada correctamente.", nivel="info")
    except Exception as e:
        capturar_log_bod1(f"Error al guardar configuración: {e}", nivel="error")


# ---------- (Opcional) Inicializar Logging Base (si aún lo usas en alguna parte) ----------
def setup_logging():
    from datetime import datetime
    from logging import INFO, basicConfig

    LOG_FILE = Path("logs") / f"fallback_log_{datetime.now().strftime('%Y%m%d')}.log"
    LOG_FILE.parent.mkdir(exist_ok=True)

    basicConfig(
        filename=LOG_FILE,
        level=INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )


def drop_duplicates_reference_master(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina duplicados de 'Reference' solo si el 'masterTrackingNumber' también se repite.
    """
    if "Reference" in df.columns and "masterTrackingNumber" in df.columns:
        # Aseguramos tipos string por seguridad
        df["Reference"] = df["Reference"].astype(str)
        df["masterTrackingNumber"] = df["masterTrackingNumber"].astype(str)
        return df.drop_duplicates(subset=["Reference", "masterTrackingNumber"])
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
