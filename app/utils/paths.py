import os
import sys

def resource_path(relative_path):
    """
    Devuelve la ruta absoluta para archivos externos, compatible con PyInstaller.
    Si está en modo .exe (sys.frozen), usa sys._MEIPASS como base.
    """
    try:
        # Ejecutable generado por PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # Entorno de desarrollo
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Rutas absolutas
CONFIG_PATH = resource_path("excel_printer_config.json")
DB_PATH = resource_path("excel_printer.db")


import logging
from pathlib import Path
from datetime import datetime
import inspect
import os

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
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical
    }.get(nivel.lower(), logger.info)(mensaje)
