from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.db.models import Base, HistorialArchivo, RegistroImpresion
from app.core.logger_eventos import log_evento
from pathlib import Path
from datetime import datetime
import shutil

# --- Configuración de rutas y motor de base de datos ---
DATABASE_PATH = Path("data/excel_printer.db")
BACKUP_PATH = Path("data/excel_printer_backup.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Asegura la carpeta data
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Crea el motor y la sesión
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# --- Inicialización de la Base de Datos ---
def init_db():
    """
    Inicializa la base de datos. Si falla y hay respaldo, lo restaura automáticamente.
    """
    try:
        log_evento("Inicializando base de datos...", "info")
        Base.metadata.create_all(bind=engine)
        log_evento("Tablas creadas o verificadas correctamente.", "info")
    except OperationalError as e:
        log_evento(f"Error al inicializar base de datos: {e}", "error")

        if BACKUP_PATH.exists():
            log_evento("Respaldo encontrado. Intentando restauración...", "warning")
            try:
                shutil.copy2(BACKUP_PATH, DATABASE_PATH)
                log_evento("Respaldo restaurado. Reintentando creación de tablas...", "info")
                Base.metadata.create_all(bind=engine)
                log_evento("Base restaurada e inicializada correctamente.", "info")
            except Exception as ex:
                log_evento(f"Fallo al restaurar desde backup: {ex}", "critical")
                raise
        else:
            log_evento("No hay respaldo disponible. Intentando crear base vacía...", "warning")
            try:
                Base.metadata.create_all(bind=engine)
                log_evento("Nueva base de datos creada con éxito.", "info")
            except Exception as ex:
                log_evento(f"Fallo crítico al crear base de datos nueva: {ex}", "critical")
                raise

# --- Registro de Historial de Archivos ---
def save_file_history(filepath: str, modo: str, usuario_id: int = None):
    """
    Registra el procesamiento de un archivo en la tabla historial_archivos.
    """
    try:
        with SessionLocal() as session:
            registro = HistorialArchivo(
                usuario_id=usuario_id,
                nombre_archivo=Path(filepath).name,
                modo_utilizado=modo,
                fecha_procesado=datetime.now()
            )
            session.add(registro)
            session.commit()
            log_evento(f"Historial de archivo guardado: {filepath}", "info")
    except Exception as e:
        log_evento(f"Error al guardar historial de archivo: {e}", "error")

# --- Registro de Historial de Impresiones ---
def save_print_history(archivo: str, observacion: str = "", usuario_id: int = None):
    """
    Registra una impresión en la tabla registro_impresiones.
    """
    try:
        with SessionLocal() as session:
            registro = RegistroImpresion(
                usuario_id=usuario_id,
                archivo_impreso=archivo,
                observacion=observacion,
                fecha_impresion=datetime.now()
            )
            session.add(registro)
            session.commit()
            log_evento(f"Impresión registrada: {archivo}", "info")
    except Exception as e:
        log_evento(f"Error al registrar impresión: {e}", "error")
