import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

def _setup_eventos_logger():
    # Ruta consistente desde cualquier ubicación de ejecución
    base_dir = Path(__file__).resolve().parent.parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    eventos_log = logs_dir / "eventos.log"
    logger = logging.getLogger("eventos_logger")
    logger.setLevel(logging.INFO)

    # Evita añadir múltiples handlers
    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            eventos_log,
            when="midnight",
            backupCount=30,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

_eventos_logger = _setup_eventos_logger()

def log_evento(mensaje: str, nivel: str = "info"):
    """
    Loguea un evento funcional en 'logs/eventos.log' con el nivel dado.
    """
    nivel = nivel.lower()
    log_func = {
        "debug": _eventos_logger.debug,
        "info": _eventos_logger.info,
        "warning": _eventos_logger.warning,
        "error": _eventos_logger.error,
        "critical": _eventos_logger.critical
    }.get(nivel, _eventos_logger.info)

    log_func(mensaje)

# Alias para compatibilidad
capturar_log_bod1 = log_evento
