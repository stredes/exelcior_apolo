import os
import sys
from pathlib import Path

def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta para archivos externos, compatible con PyInstaller.
    Si está empaquetado como ejecutable, usa sys._MEIPASS como base.
    En desarrollo, usa el directorio actual como base.
    """
    try:
        # PyInstaller coloca archivos temporales en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Modo desarrollo: raíz del proyecto
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# -------------------- Rutas Absolutas de Archivos --------------------

# Ruta al archivo de configuración principal
CONFIG_PATH = Path(resource_path("app/config/excel_printer_config.json"))

# Ruta a la base de datos SQLite
DB_PATH = Path(resource_path("data/excel_printer.db"))

# Ruta al directorio de logs
LOGS_DIR = Path(resource_path("logs"))
LOGS_DIR.mkdir(exist_ok=True)

# Ruta al archivo de logs principal
LOG_FILE = LOGS_DIR / "logs_app.log"
