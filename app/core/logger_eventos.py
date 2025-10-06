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
        # Handler para archivo rotativo
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

        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Logger global de eventos funcionales
_eventos_logger = _setup_eventos_logger()

# --- Función para registrar eventos funcionales ---


def log_evento(mensaje: str, nivel: str = "info", accion: str = None, exc: Exception = None):
    """
    Registra un evento funcional de la aplicación en 'logs/eventos.log' y en la terminal.

    Args:
        mensaje (str): Descripción del evento.
        nivel (str): Nivel del evento: info, warning, error, etc.
        accion (str): Acción o contexto adicional (opcional).
        exc (Exception): Excepción a registrar (opcional).
    """
    nivel = nivel.lower()
    log_func = {
        "debug": _eventos_logger.debug,
        "info": _eventos_logger.info,
        "warning": _eventos_logger.warning,
        "error": _eventos_logger.error,
        "critical": _eventos_logger.critical
    }.get(nivel, _eventos_logger.info)

    mensaje_final = mensaje
    if accion:
        mensaje_final = f"[ACCION: {accion}] {mensaje_final}"
    if exc:
        import traceback
        exc_info = traceback.format_exception(type(exc), exc, exc.__traceback__)
        mensaje_final += f"\n[EXCEPCION] {''.join(exc_info)}"
    try:
        log_func(mensaje_final)
    except Exception as e:
        print(f"[ERROR LOG] No se pudo escribir en el log: {e}\nMensaje: {mensaje_final}")

# ⚠️ Alias legado (se eliminará próximamente)
capturar_log_bod1 = log_evento
