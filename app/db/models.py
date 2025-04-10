from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

class Configuracion(Base):
    __tablename__ = 'configuraciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=False)
    clave = Column(String(50), nullable=False)
    valor = Column(String(255), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

class HistorialArchivo(Base):
    __tablename__ = 'historial_archivos'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=True)
    nombre_archivo = Column(String(255), nullable=False)
    fecha_procesado = Column(DateTime, default=datetime.utcnow)
    modo_utilizado = Column(String(50), nullable=False)


class RegistroImpresion(Base):
    __tablename__ = 'registro_impresiones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=True)
    archivo_impreso = Column(String(255), nullable=False)
    fecha_impresion = Column(DateTime, default=datetime.utcnow)
    observacion = Column(Text, nullable=True)

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
