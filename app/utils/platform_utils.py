import platform

def is_windows() -> bool:
    return platform.system() == "Windows"

def is_linux() -> bool:
    return platform.system() == "Linux"

def imprimir_etiqueta_plataforma(path_etiqueta, impresora):
    """
    Imprime la etiqueta dependiendo del sistema operativo.
    En Windows usa Excel, en Linux usa LibreOffice.
    """
    if is_windows():
        import win32com.client
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        libro = excel.Workbooks.Open(str(path_etiqueta.resolve()))
        libro.PrintOut()
        libro.Close(False)
        excel.Quit()
    elif is_linux():
        import subprocess
        subprocess.run(["libreoffice", "--headless", "--pt", impresora, str(path_etiqueta.resolve())], check=True)
    else:
        raise NotImplementedError("Sistema operativo no soportado para impresión.")



import logging
from pathlib import Path
from datetime import datetime
import inspect
import os

def log_evento(mensaje: str, nivel: str = "info"):
    """
    Guarda logs con nombre dinámico según el archivo donde se llama.
    Ejemplo: logs/etiqueta_editor_log_20250411.log
    """

    # Detectar el nombre del archivo que llama a esta función
    frame = inspect.stack()[1]
    archivo_llamador = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{archivo_llamador}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    # Evitar duplicar handlers
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical
    }.get(nivel.lower(), logger.info)(mensaje)
