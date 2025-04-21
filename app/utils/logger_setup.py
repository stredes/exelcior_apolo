from datetime import datetime
from logging import basicConfig, INFO
from pathlib import Path
import logging
import inspect
import os


def setup_logging():
    LOG_FILE = Path("logs") / f"fallback_log_{datetime.now().strftime('%Y%m%d')}.log"
    LOG_FILE.parent.mkdir(exist_ok=True)

    basicConfig(
        filename=LOG_FILE,
        level=INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8"
    )

    # También enviar logs a consola (opcional pero recomendado)
    console = logging.StreamHandler()
    console.setLevel(INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)


def log_evento(mensaje: str, nivel: str = "info"):
    """
    Guarda logs por módulo con nombre automático del archivo llamador.
    """
    frame = inspect.stack()[1]
    archivo_llamador = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{archivo_llamador}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    getattr(logger, nivel.lower(), logger.info)(mensaje)
