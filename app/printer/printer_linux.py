import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from tkinter import messagebox


def print_document(filepath, mode, config_columns, df):
    try:
        if platform.system().lower() != "linux":
            messagebox.showerror("Error", "Este método solo es compatible con Linux.")
            return

        # Verificar comandos necesarios
        for cmd in ["libreoffice", "lp"]:
            if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                raise EnvironmentError(f"{cmd} no está disponible en el sistema.")

        # Directorio para PDF exportado
        output_dir = Path("outputs/pdf").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_output = output_dir / f"{mode}_impreso_{timestamp}.pdf"

        # Convertir Excel a PDF con libreoffice
        convert_cmd = [
            "libreoffice", "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(filepath)
        ]
        result = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise RuntimeError(f"Error al convertir a PDF:\n{result.stderr.decode()}")

        generated_pdf = output_dir / Path(filepath).with_suffix('.pdf').name
        if not generated_pdf.exists():
            raise FileNotFoundError("No se encontró el PDF generado.")

        generated_pdf.rename(pdf_output)

        # Preparar comando de impresión
        print_cmd = ["lp", "-d", os.getenv("PRINTER", ""), str(pdf_output)]
        subprocess.run(print_cmd)

        messagebox.showinfo("Impresión", f"Archivo PDF impreso:\n{pdf_output.name}")

    except Exception as e:
        messagebox.showerror("Error", f"Error impresión en Linux:\n{e}")

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
