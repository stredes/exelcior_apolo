from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from app.security.passwords import hash_password, verify_password, looks_hashed

Base = declarative_base()

# -------------------------------
# 🧍 Modelo de Usuario
# -------------------------------
class User(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    configuraciones = relationship("Configuracion", back_populates="usuario", cascade="all, delete-orphan")
    historial_archivos = relationship("HistorialArchivo", back_populates="usuario", cascade="all, delete-orphan")
    impresiones = relationship("RegistroImpresion", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(nombre='{self.nombre}', email='{self.email}')>"

    def set_password(self, raw_password: str) -> None:
        self.password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self.password)

    def upgrade_password_hash_if_needed(self) -> bool:
        if looks_hashed(self.password):
            return False
        self.password = hash_password(self.password)
        return True

# -------------------------------
# ⚙️ Configuración de usuario
# -------------------------------
class Configuracion(Base):
    __tablename__ = 'configuraciones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    clave = Column(String(50), nullable=False)
    valor = Column(String(255), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Relación inversa
    usuario = relationship("User", back_populates="configuraciones")

# -------------------------------
# 📄 Historial de archivos procesados
# -------------------------------
class HistorialArchivo(Base):
    __tablename__ = 'historial_archivos'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    nombre_archivo = Column(String(255), nullable=False)
    fecha_procesado = Column(DateTime, default=datetime.utcnow)
    modo_utilizado = Column(String(50), nullable=False)

    # Relación inversa
    usuario = relationship("User", back_populates="historial_archivos")

# -------------------------------
# 🖨️ Registro de impresiones realizadas
# -------------------------------
class RegistroImpresion(Base):
    __tablename__ = 'registro_impresiones'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    archivo_impreso = Column(String(255), nullable=False)
    fecha_impresion = Column(DateTime, default=datetime.utcnow)
    observacion = Column(Text, nullable=True)

    # Relación inversa
    usuario = relationship("User", back_populates="impresiones")
