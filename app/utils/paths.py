import os
import sys

def resource_path(relative_path):
    """
    Devuelve la ruta absoluta para archivos externos, compatible con PyInstaller.
    Si está en modo .exe (sys.frozen), usa sys._MEIPASS como base.
    """
    try:
        # Ejecutable generado por PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # Entorno de desarrollo
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Rutas absolutas
CONFIG_PATH = resource_path("excel_printer_config.json")
DB_PATH = resource_path("excel_printer.db")
