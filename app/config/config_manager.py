import json
from pathlib import Path
from typing import Any, Dict

from app.utils import validate_config_structure
from app.core.logger_eventos import log_evento

CONFIG_PATH = Path("app/config/excel_printer_config.json")


def load_config() -> Dict[str, Any]:
    """
    Carga y valida la configuración desde el archivo JSON principal.
    """
    try:
        with CONFIG_PATH.open(encoding='utf-8') as f:
            config = json.load(f)
        validate_config_structure(config)
        log_evento("Configuración cargada correctamente.", "info")
        return config
    except Exception as e:
        log_evento(f"Error al cargar configuración: {e}", "error")
        return {}


def save_config(config: Dict[str, Any]) -> bool:
    """
    Guarda la configuración modificada en el archivo JSON.
    """
    try:
        with CONFIG_PATH.open("w", encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        log_evento("Configuración guardada correctamente.", "info")
        return True
    except Exception as e:
        log_evento(f"Error al guardar configuración: {e}", "error")
        return False
