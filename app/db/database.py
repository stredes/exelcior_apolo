from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.db.models import Base, User, Configuracion, HistorialArchivo, RegistroImpresion
from pathlib import Path
from datetime import datetime
import logging

# Configuración de la base de datos
DATABASE_PATH = Path("data/excel_printer.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
BACKUP_PATH = Path("data/excel_printer_backup.db")

DATABASE_PATH.parent.mkdir(exist_ok=True, parents=True)

# Motor de conexión y sesión
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    try:
        logging.info("Conectando a la base de datos...")
        Base.metadata.create_all(bind=engine)
        logging.info("Tablas verificadas o creadas correctamente.")
    except OperationalError as e:
        logging.error(f"Error al conectar/crear la BD: {e}")
        if BACKUP_PATH.exists():
            logging.info("Intentando restaurar respaldo...")
            try:
                backup_engine = create_engine(f"sqlite:///{BACKUP_PATH}")
                backup_conn = backup_engine.connect()
                logging.info("Respaldo encontrado y listo para uso.")
                backup_conn.close()
            except Exception as err:
                logging.error(f"No se pudo restaurar el respaldo: {err}")
        else:
            logging.info("No se encontró respaldo. Intentando crear nueva base de datos.")
            try:
                Base.metadata.create_all(bind=engine)
                logging.info("Nueva base de datos creada exitosamente.")
            except Exception as err:
                logging.error(f"Error creando nueva base de datos: {err}")


def save_file_history(filepath: str, modo: str, usuario_id: int = None):
    """Guarda un registro en historial_archivos"""
    session = SessionLocal()
    try:
        nuevo_registro = HistorialArchivo(
            usuario_id=usuario_id,
            nombre_archivo=Path(filepath).name,
            modo_utilizado=modo,
            fecha_procesado=datetime.now()
        )
        session.add(nuevo_registro)
        session.commit()
        logging.info(f"Historial registrado correctamente: {filepath}")
    except Exception as e:
        logging.error(f"Error al guardar historial: {e}")
        session.rollback()
    finally:
        session.close()
