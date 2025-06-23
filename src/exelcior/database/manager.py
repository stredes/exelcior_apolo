"""
Sistema de base de datos refactorizado para Exelcior Apolo.

Proporciona una interfaz limpia y robusta para todas las operaciones
de base de datos con manejo de errores mejorado y patrones modernos.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from contextlib import contextmanager
import shutil

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..config import config_manager
from ..utils import get_logger, DatabaseError

logger = get_logger("exelcior.database")

Base = declarative_base()


class FileHistory(Base):
    """Modelo para historial de archivos procesados."""
    
    __tablename__ = "file_history"
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    mode = Column(String(50), nullable=False)
    file_size = Column(Integer)  # Tamaño en bytes
    rows_processed = Column(Integer)
    processing_time = Column(Float)  # Tiempo en segundos
    created_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "mode": self.mode,
            "file_size": self.file_size,
            "rows_processed": self.rows_processed,
            "processing_time": self.processing_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "success": self.success,
            "error_message": self.error_message
        }


class PrintHistory(Base):
    """Modelo para historial de impresiones."""
    
    __tablename__ = "print_history"
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False)
    printer_name = Column(String(100))
    print_type = Column(String(50))  # PDF, Direct, Zebra
    pages_printed = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "printer_name": self.printer_name,
            "print_type": self.print_type,
            "pages_printed": self.pages_printed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "success": self.success,
            "error_message": self.error_message
        }


class Configuration(Base):
    """Modelo para configuraciones persistentes."""
    
    __tablename__ = "configuration"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    category = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class DatabaseManager:
    """
    Gestor principal de base de datos.
    
    Maneja todas las operaciones de base de datos con patrones modernos,
    manejo robusto de errores y backup automático.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa el gestor de base de datos.
        
        Args:
            db_path: Ruta de la base de datos. Si es None, usa configuración.
        """
        self.db_path = db_path or Path(config_manager.database.name)
        self.backup_path = Path(config_manager.database.backup_name)
        
        # Crear URL de conexión
        self.database_url = f"sqlite:///{self.db_path}"
        
        # Configurar engine
        self.engine = create_engine(
            self.database_url,
            echo=config_manager.database.echo_sql,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False}
        )
        
        # Configurar session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self._initialized = False

    def initialize(self) -> None:
        """Inicializa la base de datos creando tablas si es necesario."""
        try:
            # Crear backup si existe base de datos
            if self.db_path.exists():
                self._create_backup()
            
            # Crear todas las tablas
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            logger.info("Base de datos inicializada correctamente")
            
        except SQLAlchemyError as e:
            logger.error(f"Error al inicializar base de datos: {e}")
            self._restore_from_backup()
            raise DatabaseError(f"Error de inicialización: {str(e)}")

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager para sesiones de base de datos.
        
        Yields:
            Sesión de SQLAlchemy
        """
        if not self._initialized:
            self.initialize()
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error en sesión de base de datos: {e}")
            raise DatabaseError(f"Error de base de datos: {str(e)}")
        finally:
            session.close()

    def save_file_history(
        self,
        file_path: Union[str, Path],
        mode: str,
        file_size: Optional[int] = None,
        rows_processed: Optional[int] = None,
        processing_time: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> int:
        """
        Guarda un registro en el historial de archivos.
        
        Args:
            file_path: Ruta del archivo procesado
            mode: Modo de operación utilizado
            file_size: Tamaño del archivo en bytes
            rows_processed: Número de filas procesadas
            processing_time: Tiempo de procesamiento en segundos
            success: Si el procesamiento fue exitoso
            error_message: Mensaje de error si aplica
            
        Returns:
            ID del registro creado
        """
        try:
            path = Path(file_path)
            
            with self.get_session() as session:
                history_record = FileHistory(
                    file_path=str(path.absolute()),
                    file_name=path.name,
                    mode=mode,
                    file_size=file_size,
                    rows_processed=rows_processed,
                    processing_time=processing_time,
                    success=success,
                    error_message=error_message
                )
                
                session.add(history_record)
                session.flush()
                
                record_id = history_record.id
                logger.info(f"Historial de archivo guardado: {path.name} (ID: {record_id})")
                return record_id
                
        except Exception as e:
            logger.error(f"Error al guardar historial: {e}")
            raise DatabaseError(f"No se pudo guardar historial: {str(e)}")

    def save_print_history(
        self,
        file_path: Union[str, Path],
        printer_name: Optional[str] = None,
        print_type: str = "PDF",
        pages_printed: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> int:
        """
        Guarda un registro en el historial de impresiones.
        
        Args:
            file_path: Ruta del archivo impreso
            printer_name: Nombre de la impresora
            print_type: Tipo de impresión (PDF, Direct, Zebra)
            pages_printed: Número de páginas impresas
            success: Si la impresión fue exitosa
            error_message: Mensaje de error si aplica
            
        Returns:
            ID del registro creado
        """
        try:
            with self.get_session() as session:
                print_record = PrintHistory(
                    file_path=str(Path(file_path).absolute()),
                    printer_name=printer_name,
                    print_type=print_type,
                    pages_printed=pages_printed,
                    success=success,
                    error_message=error_message
                )
                
                session.add(print_record)
                session.flush()
                
                record_id = print_record.id
                logger.info(f"Historial de impresión guardado (ID: {record_id})")
                return record_id
                
        except Exception as e:
            logger.error(f"Error al guardar historial de impresión: {e}")
            raise DatabaseError(f"No se pudo guardar historial de impresión: {str(e)}")

    def get_file_history(
        self,
        limit: int = 50,
        mode: Optional[str] = None,
        success_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtiene historial de archivos procesados.
        
        Args:
            limit: Número máximo de registros
            mode: Filtrar por modo específico
            success_only: Solo registros exitosos
            
        Returns:
            Lista de diccionarios con historial
        """
        try:
            with self.get_session() as session:
                query = session.query(FileHistory)
                
                if mode:
                    query = query.filter(FileHistory.mode == mode)
                
                if success_only:
                    query = query.filter(FileHistory.success == True)
                
                records = query.order_by(FileHistory.created_at.desc()).limit(limit).all()
                
                return [record.to_dict() for record in records]
                
        except Exception as e:
            logger.error(f"Error al obtener historial: {e}")
            return []

    def get_print_history(
        self,
        limit: int = 50,
        print_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene historial de impresiones.
        
        Args:
            limit: Número máximo de registros
            print_type: Filtrar por tipo de impresión
            
        Returns:
            Lista de diccionarios con historial
        """
        try:
            with self.get_session() as session:
                query = session.query(PrintHistory)
                
                if print_type:
                    query = query.filter(PrintHistory.print_type == print_type)
                
                records = query.order_by(PrintHistory.created_at.desc()).limit(limit).all()
                
                return [record.to_dict() for record in records]
                
        except Exception as e:
            logger.error(f"Error al obtener historial de impresión: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de la aplicación.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            with self.get_session() as session:
                # Estadísticas de archivos
                total_files = session.query(FileHistory).count()
                successful_files = session.query(FileHistory).filter(FileHistory.success == True).count()
                
                # Estadísticas por modo
                mode_stats = {}
                for mode in ["fedex", "urbano", "listados"]:
                    count = session.query(FileHistory).filter(FileHistory.mode == mode).count()
                    mode_stats[mode] = count
                
                # Estadísticas de impresión
                total_prints = session.query(PrintHistory).count()
                successful_prints = session.query(PrintHistory).filter(PrintHistory.success == True).count()
                
                return {
                    "files": {
                        "total": total_files,
                        "successful": successful_files,
                        "success_rate": round((successful_files / total_files * 100) if total_files > 0 else 0, 2),
                        "by_mode": mode_stats
                    },
                    "prints": {
                        "total": total_prints,
                        "successful": successful_prints,
                        "success_rate": round((successful_prints / total_prints * 100) if total_prints > 0 else 0, 2)
                    },
                    "database": {
                        "size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2) if self.db_path.exists() else 0,
                        "last_backup": self.backup_path.stat().st_mtime if self.backup_path.exists() else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {}

    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Limpia registros antiguos de la base de datos.
        
        Args:
            days: Días de antigüedad para eliminar
            
        Returns:
            Número de registros eliminados
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            with self.get_session() as session:
                # Eliminar historial de archivos antiguos
                deleted_files = session.query(FileHistory).filter(
                    FileHistory.created_at < cutoff_date
                ).delete()
                
                # Eliminar historial de impresiones antiguas
                deleted_prints = session.query(PrintHistory).filter(
                    PrintHistory.created_at < cutoff_date
                ).delete()
                
                total_deleted = deleted_files + deleted_prints
                logger.info(f"Eliminados {total_deleted} registros antiguos (>{days} días)")
                return total_deleted
                
        except Exception as e:
            logger.error(f"Error en limpieza: {e}")
            return 0

    def _create_backup(self) -> None:
        """Crea un backup de la base de datos actual."""
        try:
            if self.db_path.exists():
                shutil.copy2(self.db_path, self.backup_path)
                logger.info(f"Backup creado: {self.backup_path}")
        except Exception as e:
            logger.warning(f"No se pudo crear backup: {e}")

    def _restore_from_backup(self) -> None:
        """Restaura la base de datos desde backup."""
        try:
            if self.backup_path.exists():
                shutil.copy2(self.backup_path, self.db_path)
                logger.info("Base de datos restaurada desde backup")
            else:
                logger.warning("No hay backup disponible para restaurar")
        except Exception as e:
            logger.error(f"Error al restaurar backup: {e}")

    def export_data(self, output_path: Path, format: str = "json") -> None:
        """
        Exporta todos los datos de la base de datos.
        
        Args:
            output_path: Ruta del archivo de exportación
            format: Formato de exportación (json, csv)
        """
        try:
            with self.get_session() as session:
                data = {
                    "file_history": [record.to_dict() for record in session.query(FileHistory).all()],
                    "print_history": [record.to_dict() for record in session.query(PrintHistory).all()],
                    "export_date": datetime.utcnow().isoformat()
                }
                
                if format.lower() == "json":
                    import json
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Formato no soportado: {format}")
                
                logger.info(f"Datos exportados a: {output_path}")
                
        except Exception as e:
            logger.error(f"Error al exportar datos: {e}")
            raise DatabaseError(f"No se pudieron exportar datos: {str(e)}")


# Instancia global del gestor de base de datos
database_manager = DatabaseManager()

