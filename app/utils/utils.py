import json
from pathlib import Path
from app.core.logger_bod1 import capturar_log_bod1

# Ruta del archivo de configuración
CONFIG_FILE = Path("excel_printer_config.json")

# ---------- Cargar Configuración ----------
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                capturar_log_bod1("Configuración cargada correctamente", nivel="info")
                return config
        except Exception as e:
            capturar_log_bod1(f"Error al cargar configuración: {e}", nivel="error")
            return {}
    else:
        capturar_log_bod1("Archivo de configuración no encontrado. Se cargará configuración vacía", nivel="warning")
        return {}

# ---------- Guardar Configuración ----------
def save_config(config_data):
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
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=4)
        capturar_log_bod1("Configuración guardada correctamente.", nivel="info")
    except Exception as e:
        capturar_log_bod1(f"Error al guardar configuración: {e}", nivel="error")

# ---------- (Opcional) Inicializar Logging Base (si aún lo usas en alguna parte) ----------
def setup_logging():
    from datetime import datetime
    from logging import basicConfig, INFO

    LOG_FILE = Path("logs") / f"fallback_log_{datetime.now().strftime('%Y%m%d')}.log"
    LOG_FILE.parent.mkdir(exist_ok=True)

    basicConfig(
        filename=LOG_FILE,
        level=INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8"
    )
