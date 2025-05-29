# M�dulo: printer_etiquetas.py
# Descripci�n: L�gica de impresi�n correspondiente.

# Módulo: printer_etiquetas.py
# Descripción: Lógica de impresión de etiquetas (Zebra o similares)

import os
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
from app.core.logger_eventos import log_evento

def imprimir_etiquetas_zebra(etiquetas: list[str], puerto: str = "LPT1"):
    """
    Envía líneas de código ZPL directamente a una impresora Zebra conectada al puerto especificado.
    """
    try:
        if not etiquetas:
            raise ValueError("La lista de etiquetas está vacía.")

        with open(puerto, "w", encoding="utf-8") as printer:
            for zpl in etiquetas:
                printer.write(zpl + "\n")

        log_evento(f"{len(etiquetas)} etiquetas enviadas a {puerto}", "info")

    except Exception as e:
        log_evento(f"Error al imprimir etiquetas: {e}", "error")
        messagebox.showerror("Error", f"No se pudo imprimir etiquetas: {e}")
