from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from pathlib import Path
import json
import logging
from datetime import datetime
from app.db.models import HistorialArchivo

# Configuración inicial de paths
CONFIG_FILE = Path("app/config/excel_printer_config.json")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "logs_app.log"

# ----------------- Setup Logging -----------------
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

setup_logging()

# ----------------- Conexión a la BD -----------------
DB_PATH = Path("data/excel_printer.db")
DB_PATH.parent.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


# ----------------- Configuración -----------------
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return validate_config_structure(config)
        except Exception as e:
            logging.error(f"Error al cargar configuración: {e}")
            return {}
    return {}

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
        CONFIG_FILE.parent.mkdir(exist_ok=True, parents=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(convert_sets(config_data), f, indent=4)
        logging.info("Configuración guardada correctamente.")
    except Exception as e:
        logging.error(f"Error al guardar configuración: {e}")

def validate_config_structure(config):
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

def guardar_ultimo_path(path_str: str, clave: str = "ultimo_archivo_excel"):
    try:
        config = load_config()
        config[clave] = str(Path(path_str).resolve())
        save_config(config)
        logging.info(f"Ruta guardada en config ({clave}): {path_str}")
    except Exception as e:
        logging.error(f"Error al guardar ruta en config: {e}")


# ----------------- Historial Archivos -----------------
def save_file_history(nombre_archivo, modo, usuario_id=None):
    session = Session()
    try:
        record = HistorialArchivo(
            usuario_id=usuario_id,
            nombre_archivo=str(nombre_archivo),
            fecha_procesado=datetime.utcnow(),
            modo_utilizado=modo
        )
        session.add(record)
        session.commit()
        logging.info(f"Historial guardado para archivo '{nombre_archivo}' en modo '{modo}'")
    except Exception as e:
        session.rollback()
        logging.error(f"Error al guardar historial: {e}")
    finally:
        session.close()
