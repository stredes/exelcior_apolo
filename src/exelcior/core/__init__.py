"""
Módulo core de Exelcior Apolo.

Contiene la lógica de negocio principal y los procesadores
fundamentales de la aplicación.
"""

from .excel_processor import ExcelProcessor, excel_processor
from .autoloader import AutoLoader, FilePattern, autoloader

__all__ = [
    "ExcelProcessor",
    "excel_processor",
    "AutoLoader", 
    "FilePattern",
    "autoloader"
]

