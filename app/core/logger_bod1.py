# utils/logger_bod1.py

import logging
from pathlib import Path
from datetime import datetime

def capturar_log_bod1(mensaje: str, nivel: str = "info"):
    """
    Guarda un mensaje en un log separado tipo 'logs/bod1_log_YYYYMMDD.log'.
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    fecha_actual = datetime.now().strftime("%Y%m%d")
    nombre_log = logs_dir / f"bod1_log_{fecha_actual}.log"

    logger = logging.getLogger("bod1_logger")
    logger.setLevel(logging.DEBUG)

    # Evitar múltiples handlers duplicados
    if not logger.handlers:
        fh = logging.FileHandler(nombre_log, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(fh)

    nivel = nivel.lower()
    log_func = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical
    }.get(nivel, logger.info)

    log_func(mensaje)
