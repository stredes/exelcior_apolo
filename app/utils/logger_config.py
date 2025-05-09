# app/utils/logger_config.py
import logging
import sys

class ColorFormatter(logging.Formatter):
    RED = "\033[31m"
    RESET = "\033[0m"

    def format(self, record):
        msg = super().format(record)
        if record.levelno >= logging.ERROR:
            return f"{self.RED}{msg}{self.RESET}"
        return msg


def setup_logging(level: int = logging.DEBUG):
    """
    Configura el logger raíz para que:
      - Muestre todos los niveles desde `level` en consola.
      - Pinte de rojo (`RED`) solo los errores (>= ERROR).
    """
    root = logging.getLogger()
    root.setLevel(level)
    # Eliminar handlers previos
    for h in list(root.handlers):
        root.removeHandler(h)

    # Handler de consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ch.setFormatter(ColorFormatter(fmt))
    root.addHandler(ch)

