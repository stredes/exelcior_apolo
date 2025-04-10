# utils/logger_bod1.py

import logging
from pathlib import Path
from datetime import datetime

def capturar_log_bod1(mensaje: str, nivel: str = "info"):
    """
    Guarda un mensaje en un log tipo 'logs/bod1_log_YYYYMMDD.log'.
    Nivel puede ser: debug, info, warning, error, critical.
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    fecha_actual = datetime.now().strftime("%Y%m%d")
    nombre_log = logs_dir / f"bod1_log_{fecha_actual}.log"

    logger = logging.getLogger("bod1_logger")
    logger.setLevel(logging.DEBUG)

    # Verifica si ya hay un handler asociado al archivo
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(nombre_log.resolve()) for h in logger.handlers):
        file_handler = logging.FileHandler(nombre_log, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Selección de función de log según nivel
    nivel = nivel.lower()
    log_func = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical
    }.get(nivel, logger.info)

    log_func(mensaje)
