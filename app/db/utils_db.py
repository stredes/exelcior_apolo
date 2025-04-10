from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from pathlib import Path
import json
import logging
from datetime import datetime

from .models import Base, User, Configuracion, HistorialArchivo, RegistroImpresion

# Rutas de configuración
CONFIG_FILE = Path("excel_printer_config.json")
LOG_FILE = Path("logs_app.log")

# ----------------- Conexión a la BD -----------------
DB_PATH = "sqlite:///excel_printer.db"
engine = create_engine(DB_PATH)
Session = sessionmaker(bind=engine)

# ----------------- Configuración -----------------
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error al cargar configuración: {e}")
            return {}
    return {}

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        logging.info("Configuración guardada correctamente.")
    except Exception as e:
        logging.error(f"Error al guardar configuración: {e}")

# ----------------- Usuarios -----------------
def create_user(username, password):
    session = Session()
    try:
        user = User(username=username, password=password)
        session.add(user)
        session.commit()
        logging.info(f"Usuario '{username}' creado.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error al crear usuario: {e}")
    finally:
        session.close()

def get_user(username):
    session = Session()
    try:
        return session.query(User).filter_by(username=username).first()
    except Exception as e:
        logging.error(f"Error al obtener usuario: {e}")
        return None
    finally:
        session.close()

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

# ----------------- Logging -----------------
def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


import logging
from pathlib import Path
from datetime import datetime
import inspect
import os

def log_evento(mensaje: str, nivel: str = "info"):
    """
    Guarda logs con nombre dinámico según el archivo donde se llama.
    Ejemplo: logs/etiqueta_editor_log_20250411.log
    """

    # Detectar el nombre del archivo que llama a esta función
    frame = inspect.stack()[1]
    archivo_llamador = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{archivo_llamador}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    # Evitar duplicar handlers
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical
    }.get(nivel.lower(), logger.info)(mensaje)
