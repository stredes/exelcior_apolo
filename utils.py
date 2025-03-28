import json
from pathlib import Path
import logging

# Ruta del archivo de configuración
CONFIG_FILE = Path("excel_printer_config.json")

# Ruta del archivo de logs
LOG_FILE = Path("logs_app.log")

# ---------- Configuración Inicial ----------
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error al cargar configuración: {e}")
            return {}
    return {}

# ---------- Guardar Configuración ----------
def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        logging.info("Configuración guardada correctamente.")
    except Exception as e:
        logging.error(f"Error al guardar configuración: {e}")

# ---------- Configuración de Logging ----------
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
