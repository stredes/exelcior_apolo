from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Configuracion(Base):
    __tablename__ = "configuraciones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=False)
    clave = Column(String(50), nullable=False)
    valor = Column(String(255), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)


class HistorialArchivo(Base):
    __tablename__ = "historial_archivos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=True)
    nombre_archivo = Column(String(255), nullable=False)
    fecha_procesado = Column(DateTime, default=datetime.utcnow)
    modo_utilizado = Column(
        String(50), nullable=False
    )  # Este campo es correcto si usas modo_utilizado en el insert


class RegistroImpresion(Base):
    __tablename__ = "registro_impresiones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=True)
    archivo_impreso = Column(String(255), nullable=False)
    fecha_impresion = Column(DateTime, default=datetime.utcnow)
    observacion = Column(Text, nullable=True)
