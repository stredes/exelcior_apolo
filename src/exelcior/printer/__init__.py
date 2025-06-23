"""
Módulo de impresión para Exelcior Apolo.

Proporciona una interfaz unificada para diferentes tipos de impresión
incluyendo impresoras del sistema, Zebra y exportación a PDF.
"""

from .manager import (
    PrintManager,
    PrinterInterface,
    SystemPrinter,
    ZebraPrinter,
    PDFExporter,
    print_manager
)

__all__ = [
    "PrintManager",
    "PrinterInterface",
    "SystemPrinter",
    "ZebraPrinter", 
    "PDFExporter",
    "print_manager"
]

