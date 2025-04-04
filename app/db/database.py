from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from .models import Base, User, Configuracion, HistorialArchivo, RegistroImpresion
from pathlib import Path
from datetime import datetime
import logging

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
            logging.info("No se encontró respaldo. Intentando crear nueva base de datos.")
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
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        session.add(nuevo_registro)
        session.commit()
        logging.info(f"Historial registrado: {filepath}")
    except Exception as e:
        logging.error(f"Error al guardar historial: {e}")
        session.rollback()
    finally:
        session.close()