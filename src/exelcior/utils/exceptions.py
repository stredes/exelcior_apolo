"""
Sistema de excepciones personalizado para Exelcior Apolo.

Define excepciones específicas de la aplicación para un mejor
manejo de errores y debugging.
"""

from typing import Optional, Any


class ExelciorError(Exception):
    """Excepción base para todas las excepciones de Exelcior."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Any] = None):
        """
        Inicializa la excepción.
        
        Args:
            message: Mensaje de error
            error_code: Código de error opcional
            details: Detalles adicionales del error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class FileProcessingError(ExelciorError):
    """Excepción para errores de procesamiento de archivos."""
    pass


class DatabaseError(ExelciorError):
    """Excepción para errores de base de datos."""
    pass


class ConfigurationError(ExelciorError):
    """Excepción para errores de configuración."""
    pass


class NetworkError(ExelciorError):
    """Excepción para errores de red."""
    pass


class ValidationError(ExelciorError):
    """Excepción para errores de validación."""
    pass


class PrinterError(ExelciorError):
    """Excepción para errores de impresión."""
    pass


class GUIError(ExelciorError):
    """Excepción para errores de interfaz gráfica."""
    pass


class ExportError(ExelciorError):
    """Excepción para errores de exportación."""
    pass

