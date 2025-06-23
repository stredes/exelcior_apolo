"""
Módulo de utilidades para Exelcior Apolo.

Proporciona funciones y clases de utilidad comunes
utilizadas en toda la aplicación.
"""

from .logging import get_logger, logger_setup
from .exceptions import (
    ExelciorError,
    FileProcessingError,
    DatabaseError,
    ConfigurationError,
    NetworkError,
    ValidationError,
    PrinterError,
    GUIError,
    ExportError
)
from .validators import (
    FileValidator,
    DataValidator,
    NetworkValidator,
    ConfigValidator
)

__all__ = [
    # Logging
    "get_logger",
    "logger_setup",
    
    # Exceptions
    "ExelciorError",
    "FileProcessingError",
    "DatabaseError",
    "ConfigurationError",
    "NetworkError",
    "ValidationError",
    "PrinterError",
    "GUIError",
    "ExportError",
    
    # Validators
    "FileValidator",
    "DataValidator",
    "NetworkValidator",
    "ConfigValidator"
]

