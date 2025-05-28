# app/utils/logger_setup.py

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def setup_logging():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Log general (app.log)
    app_log = logs_dir / "app.log"
    app_handler = TimedRotatingFileHandler(app_log, when="midnight", backupCount=10, encoding="utf-8")
    app_format = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    app_handler.setFormatter(app_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        root_logger.addHandler(app_handler)

    # Log de eventos funcionales (eventos.log)
    eventos_log = logs_dir / "eventos.log"
    eventos_handler = TimedRotatingFileHandler(eventos_log, when="midnight", backupCount=10, encoding="utf-8")
    eventos_format = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    eventos_handler.setFormatter(eventos_format)

    eventos_logger = logging.getLogger("eventos_logger")
    eventos_logger.setLevel(logging.INFO)
    if not eventos_logger.handlers:
        eventos_logger.addHandler(eventos_handler)

    root_logger.info("🟢 Sistema de logging inicializado correctamente.")
