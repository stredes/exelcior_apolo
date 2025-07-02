import json
from pathlib import Path
from app.core.logger_eventos import capturar_log_bod1
from app.utils.paths import CONFIG_PATH  # ← Se importa la ruta centralizada

# ---------- Cargar Configuración ----------
def load_config() -> dict:
    """
    Carga la configuración desde el archivo JSON principal.
    Retorna un diccionario con la configuración o uno vacío en caso de error.
    """
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                config = validate_config_structure(config)
                capturar_log_bod1("Configuración cargada correctamente", nivel="info")
                return config
        except Exception as e:
            capturar_log_bod1(f"Error al cargar configuración: {e}", nivel="error")
            return {}
    else:
        capturar_log_bod1("Archivo de configuración no encontrado. Se cargará configuración vacía", nivel="warning")
        return {}

# Alias directo por si se desea importar con otro nombre
def load_config_from_file() -> dict:
    return load_config()

# ---------- Guardar Configuración ----------
def save_config(config_data: dict):
    """
    Guarda la configuración como JSON en el archivo de configuración principal.
    Convierte automáticamente los sets a listas para compatibilidad con JSON.
    """
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        return obj

    try:
        serializable_data = convert_sets(config_data)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=4)
        capturar_log_bod1("Configuración guardada correctamente.", nivel="info")
    except Exception as e:
        capturar_log_bod1(f"Error al guardar configuración: {e}", nivel="error")

# ---------- Validación de estructura de configuración ----------
def validate_config_structure(config: dict) -> dict:
    """
    Asegura que la configuración tenga todas las claves necesarias por modo.
    Si falta alguna sección, la inicializa con valores por defecto.
    """
    modos = ["fedex", "urbano", "listados"]
    for modo in modos:
        if modo not in config:
            config[modo] = {}
        config[modo].setdefault("eliminar", [])
        config[modo].setdefault("sumar", [])
        config[modo].setdefault("mantener_formato", [])
        config[modo].setdefault("start_row", 0)
        config[modo].setdefault("nombre_archivo_digitos", [])
        config[modo].setdefault("vista_previa_fuente", 10)
    return config

# ---------- Guardar ruta de último archivo usado ----------
def guardar_ultimo_path(path_str: str, clave: str = "ultimo_archivo_excel"):
    """
    Guarda la ruta del último archivo Excel procesado, para reabrirlo más adelante.
    """
    try:
        config = load_config()
        config[clave] = str(Path(path_str).resolve())
        save_config(config)
        capturar_log_bod1(f"Ruta guardada en config ({clave}): {path_str}", nivel="info")
    except Exception as e:
        capturar_log_bod1(f"Error al guardar ruta en config: {e}", nivel="error")
