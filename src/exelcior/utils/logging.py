"""
Sistema de logging centralizado y mejorado para Exelcior Apolo.

Proporciona configuración consistente de logging con rotación de archivos,
diferentes niveles y formateo apropiado.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from ..constants import LOGGING_CONFIG


class LoggerSetup:
    """
    Configurador centralizado de logging.
    
    Maneja la configuración de loggers con rotación de archivos,
    formateo consistente y diferentes niveles de logging.
    """

    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Inicializa el configurador de logging.
        
        Args:
            logs_dir: Directorio donde almacenar logs. Si es None, usa 'logs'.
        """
        self.logs_dir = logs_dir or Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        self._configured_loggers = set()

    def setup_logger(
        self, 
        name: str, 
        level: str = LOGGING_CONFIG["level"],
        log_to_file: bool = True,
        log_to_console: bool = True
    ) -> logging.Logger:
        """
        Configura un logger con las especificaciones dadas.
        
        Args:
            name: Nombre del logger
            level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Si debe escribir a archivo
            log_to_console: Si debe escribir a consola
            
        Returns:
            Logger configurado
        """
        logger = logging.getLogger(name)
        
        # Evitar configuración duplicada
        if name in self._configured_loggers:
            return logger
        
        logger.setLevel(getattr(logging, level.upper()))
        
        # Formatter común
        formatter = logging.Formatter(
            LOGGING_CONFIG["format"],
            datefmt=LOGGING_CONFIG["date_format"]
        )
        
        # Handler para archivo con rotación
        if log_to_file:
            log_file = self.logs_dir / f"{name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=LOGGING_CONFIG["max_file_size_mb"] * 1024 * 1024,
                backupCount=LOGGING_CONFIG["backup_count"],
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Handler para consola
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        self._configured_loggers.add(name)
        return logger

    def setup_application_loggers(self) -> None:
        """Configura todos los loggers principales de la aplicación."""
        loggers = [
            "exelcior.main",
            "exelcior.core",
            "exelcior.database",
            "exelcior.gui",
            "exelcior.printer",
            "exelcior.config",
            "exelcior.utils"
        ]
        
        for logger_name in loggers:
            self.setup_logger(logger_name)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtiene un logger configurado.
        
        Args:
            name: Nombre del logger
            
        Returns:
            Logger configurado
        """
        if name not in self._configured_loggers:
            return self.setup_logger(name)
        return logging.getLogger(name)


# Instancia global del configurador de logging
logger_setup = LoggerSetup()

# Configurar loggers principales al importar
logger_setup.setup_application_loggers()


def get_logger(name: str) -> logging.Logger:
    """
    Función de conveniencia para obtener un logger configurado.
    
    Args:
        name: Nombre del logger
        
    Returns:
        Logger configurado
    """
    return logger_setup.get_logger(name)

