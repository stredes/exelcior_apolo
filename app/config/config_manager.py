import json
from pathlib import Path
from typing import Any, Dict

from app.utils.validate_config_structure import validate_config_structure
from app.core.logger_eventos import log_evento

# Ruta fija al archivo de configuración del sistema
CONFIG_PATH = Path("app/config/excel_printer_config.json")


def load_config() -> Dict[str, Any]:
    """
    Carga y valida la configuración desde el archivo JSON principal.
    Retorna un diccionario con la configuración. Si falla, retorna {}.
    """
    try:
        with CONFIG_PATH.open(encoding='utf-8') as f:
            config = json.load(f)
        config = validate_config_structure(config)
        log_evento("✅ Configuración cargada correctamente.", "info")
        return config
    except Exception as e:
        log_evento(f"❌ Error al cargar configuración: {e}", "error")
        return {}


def save_config(config: Dict[str, Any]) -> bool:
    """
    Guarda el diccionario de configuración en el archivo JSON.
    Convierte automáticamente sets a listas si es necesario.
    """
    try:
        def convert_sets(obj):
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_sets(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_sets(i) for i in obj]
            return obj

        cleaned_config = convert_sets(config)
        with CONFIG_PATH.open("w", encoding='utf-8') as f:
            json.dump(cleaned_config, f, indent=4, ensure_ascii=False)
        log_evento("💾 Configuración guardada correctamente.", "info")
        return True
    except Exception as e:
        log_evento(f"❌ Error al guardar configuración: {e}", "error")
        return False


def guardar_ultimo_path(path_str: str, clave: str = "ultimo_archivo_excel"):
    """
    Guarda la ruta del último archivo utilizado bajo una clave específica en la configuración.
    Ejemplo: 'archivo_inventario', 'archivo_codigos_postales', etc.
    """
    config = load_config()
    config[clave] = str(path_str)
    save_config(config)
    log_evento(f"📍 Ruta actualizada en configuración: {clave} = {path_str}")
