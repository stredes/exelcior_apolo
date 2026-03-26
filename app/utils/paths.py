import os
import sys
from pathlib import Path
from app.utils.app_dirs import CONFIG_DIR, DATA_DIR, LOGS_DIR, ensure_file

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

# Ruta al archivo de configuración principal editable por el usuario.
CONFIG_PATH = ensure_file(
    CONFIG_DIR / "excel_printer_config.json",
    legacy_candidates=(
        Path("app/config/excel_printer_config.json"),
        Path("config/excel_printer_config.json"),
    ),
)

# Ruta a la base de datos SQLite persistente del usuario.
DB_PATH = ensure_file(
    DATA_DIR / "excel_printer.db",
    legacy_candidates=(
        Path("data/excel_printer.db"),
        Path("app/db/excel_printer.db"),
    ),
)

# Ruta al directorio de logs persistentes del usuario.
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Ruta al archivo de logs principal
LOG_FILE = LOGS_DIR / "logs_app.log"
