# app/utils/utils.py

import json
from pathlib import Path
from app.core.logger_eventos import log_evento
from app.utils.validate_config_structure import validate_config_structure

from app.utils.paths import CONFIG_PATH

# === CONFIGURACIÓN ===
# Archivo de configuración principal del sistema (excel_printer_config.json)
# Se espera que este archivo esté ubicado junto al ejecutable o en la raíz del proyecto
# Claves comunes:
# - "fedex", "urbano", "listados" → config de transformación
# - "ultimo_archivo_excel", "archivo_inventario", "archivo_codigos_postales" → últimas rutas usadas

# --- Cargar configuración JSON ---
def load_config() -> dict:
    """
    Carga el archivo de configuración desde la ruta definida en CONFIG_PATH.
    Si el archivo no existe o está corrupto, retorna un diccionario vacío.
    Valida y completa estructura si hay campos faltantes.
    """
    try:
        config_file = Path(CONFIG_PATH)
        if config_file.exists():
            with config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)
                config = validate_config_structure(config)
                log_evento("✅ Configuración cargada correctamente.")
                return config
        else:
            log_evento("⚠️ Archivo de configuración no encontrado. Se usará configuración vacía.", "warning")
            return {}
    except Exception as e:
        log_evento(f"❌ Error al cargar configuración: {e}", "error")
        return {}

# --- Guardar configuración JSON ---
def save_config(config_data: dict):
    """
    Guarda el diccionario de configuración en formato JSON.
    Convierte automáticamente sets a listas (porque JSON no admite sets).
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

        cleaned_config = convert_sets(config_data)
        with Path(CONFIG_PATH).open("w", encoding="utf-8") as f:
            json.dump(cleaned_config, f, indent=4, ensure_ascii=False)
        log_evento("💾 Configuración guardada correctamente.")
    except Exception as e:
        log_evento(f"❌ Error al guardar configuración: {e}", "error")

# --- Guardar ruta de último archivo procesado ---
def guardar_ultimo_path(path_str: str, clave: str = "ultimo_archivo_excel"):
    """
    Guarda la ruta del último archivo usado en la configuración JSON bajo una clave determinada.

    Args:
        path_str (str): Ruta absoluta del archivo.
        clave (str): Clave donde guardar la ruta. Ej: 'archivo_inventario', 'archivo_codigos_postales'.
    """
    config = load_config()
    config[clave] = str(path_str)
    save_config(config)
    log_evento(f"📍 Ruta actualizada en configuración: {clave} = {path_str}")
