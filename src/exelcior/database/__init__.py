"""
Módulo de base de datos para Exelcior Apolo.

Proporciona una interfaz moderna y robusta para todas las operaciones
de persistencia de datos.
"""

from .manager import (
    DatabaseManager,
    FileHistory,
    PrintHistory,
    Configuration,
    database_manager
)

__all__ = [
    "DatabaseManager",
    "FileHistory",
    "PrintHistory", 
    "Configuration",
    "database_manager"
]

