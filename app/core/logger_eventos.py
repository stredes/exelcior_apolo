import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# --- Configuración del logger de eventos funcionales ---
def _setup_eventos_logger():
    # Calcula la ruta base del proyecto
    base_dir = Path(__file__).resolve().parent.parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "eventos.log"
    logger = logging.getLogger("eventos_logger")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Logger global de eventos funcionales
_eventos_logger = _setup_eventos_logger()

# --- Función para registrar eventos funcionales ---
def log_evento(mensaje: str, nivel: str = "info"):
    """
    Registra un evento funcional de la aplicación en 'logs/eventos.log'.

    Args:
        mensaje (str): Descripción del evento.
        nivel (str): Nivel del evento: info, warning, error, etc.
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

# ⚠️ Alias legado (se eliminará próximamente)
capturar_log_bod1 = log_evento
