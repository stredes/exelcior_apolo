import logging
from datetime import datetime
from pathlib import Path

# Creamos un logger dedicado y lo configuramos solo una vez
logger = logging.getLogger("bod1")
logger.setLevel(logging.INFO)


def capturar_log_bod1(mensaje: str, nivel: str = "info"):
    # Directorio y nombre de archivo según la fecha
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    fecha_actual = datetime.now().strftime("%Y%m%d")
    nombre_log = logs_dir / f"bod1_log_{fecha_actual}.log"

    # Si aún no tenemos un FileHandler apuntando a este archivo, lo añadimos
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == str(nombre_log)
        for h in logger.handlers
    ):
        fh = logging.FileHandler(nombre_log, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(fh)

    # Disparar el mensaje con el nivel correspondiente
    log_func = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(nivel.lower(), logger.info)

    log_func(mensaje)
