import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from .models import (Base, Configuracion, HistorialArchivo, RegistroImpresion,
                     User)

DATABASE_URL = "sqlite:///excel_printer.db"
BACKUP_PATH = Path("excel_printer_backup.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    try:
        # Intentar conectarse
        logging.info("Conectando a la base de datos...")
        Base.metadata.create_all(bind=engine)
        logging.info("Tablas verificadas o creadas correctamente.")
    except OperationalError as e:
        logging.error(f"Error al conectar/crear la BD: {e}")
        # Intentar restaurar respaldo
        if BACKUP_PATH.exists():
            logging.info("Intentando restaurar respaldo...")
            try:
                backup_engine = create_engine(f"sqlite:///{BACKUP_PATH}")
                backup_conn = backup_engine.connect()
                # Aquí puedes implementar lógica de restauración si es necesario
                logging.info("Respaldo encontrado y listo para uso.")
                backup_conn.close()
            except Exception as err:
                logging.error(f"No se pudo restaurar el respaldo: {err}")
        else:
            logging.info(
                "No se encontró respaldo. Intentando crear nueva base de datos."
            )
            try:
                Base.metadata.create_all(bind=engine)
                logging.info("Nueva base de datos creada exitosamente.")
            except Exception as err:
                logging.error(f"Error creando nueva base de datos: {err}")


def save_file_history(filepath, modo):
    session = SessionLocal()
    try:
        nuevo_registro = HistorialArchivo(
            nombre_archivo=Path(filepath).name,
            modo=modo,
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        session.add(nuevo_registro)
        session.commit()
        logging.info(f"Historial registrado: {filepath}")
    except Exception as e:
        logging.error(f"Error al guardar historial: {e}")
        session.rollback()
    finally:
        session.close()


import inspect
import logging
import os
from datetime import datetime
from pathlib import Path


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
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve())
        for h in logger.handlers
    ):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(nivel.lower(), logger.info)(mensaje)
