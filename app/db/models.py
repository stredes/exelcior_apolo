from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)  # ← hash en vez de texto plano
    creado_en = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(nombre='{self.nombre}', email='{self.email}')>"

class Configuracion(Base):
    __tablename__ = 'configuraciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    clave = Column(String(50), nullable=False)
    valor = Column(String(255), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

class HistorialArchivo(Base):
    __tablename__ = 'historial_archivos'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    nombre_archivo = Column(String(255), nullable=False)
    fecha_procesado = Column(DateTime, default=datetime.utcnow)
    modo_utilizado = Column(String(50), nullable=False)

class RegistroImpresion(Base):
    __tablename__ = 'registro_impresiones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    archivo_impreso = Column(String(255), nullable=False)
    fecha_impresion = Column(DateTime, default=datetime.utcnow)
    observacion = Column(Text, nullable=True)
