# run_app.py

from app.main_app import run_app  # ajusta si tu función de arranque tiene otro nombre
from app.config.config_manager import load_config
from app.utils.validate_config_structure import validate_config_structure
import sys

def validate_system():
    config = load_config()
    valid = validate_config_structure(config)
    if not isinstance(valid, dict):
        print("[ERROR] Configuración inválida. Verifica los archivos de configuración.")
        return False
    return True

if __name__ == "__main__":
    if validate_system():
        run_app()
    else:
        sys.exit(1)
