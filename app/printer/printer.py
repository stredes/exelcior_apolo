import logging
import platform
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import pandas as pd
from fpdf import FPDF

# Intentar importar backends de impresión
try:
    import pythoncom  # type: ignore[import]
    from win32com.client import Dispatch  # type: ignore[import]
except ImportError:
    pythoncom = None
    Dispatch = None

try:
    import cups  # type: ignore[import]
except ImportError:
    cups = None


def print_document(filepath: Path, mode: str, config_columns: dict, df: pd.DataFrame):
    """
    Genera un PDF con los datos filtrados y envía a imprimir usando:
      - Windows COM si está disponible (pythoncom + win32com.client).
      - CUPS si está disponible en Linux.
    """
    try:
        # Verificar existencia del archivo
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        # 1) Generar PDF intermedio
        pdf_path = _generar_pdf(filepath, mode, config_columns, df)

        # 2) Determinar backend de impresión
        system = platform.system()
        if system == 'Windows' and pythoncom and Dispatch:
            _print_windows(pdf_path)
        elif cups:
            _print_cups(pdf_path)
        else:
            raise EnvironmentError(
                "No se encontró un backend de impresión válido. "
                "Instala pywin32 en Windows o python3-cups/pycups en Linux."
            )

        messagebox.showinfo("Impresión exitosa", f"Enviado a imprimir: {pdf_path.name}")
        logging.info(f"Impresión completada: {pdf_path}")

    except Exception as e:
        logging.error(f"Error al imprimir {filepath}: {e}")
        messagebox.showerror("Error de impresión", f"Ocurrió un error:\n{e}")


def _generar_pdf(filepath: Path, mode: str, config_columns: dict, df: pd.DataFrame) -> Path:
    """
    Crea un PDF con:
      - Título centrado (Fin Día Urbano/Fin Día Fedex)
      - Tabla cuadriculada con columnas especificadas
      - Líneas de 'Recibe' y 'Firma'
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    title = "FIN DÍA URBANO" if mode.lower() == "urbano" else "FIN DÍA FEDEX"
    pdf.cell(0, 10, title, ln=True, align="C")

    # Columnas según configuración
    cols = config_columns.get(mode, {}).get("columns", df.columns.tolist())
    sub_df = df[cols]

    # Tabla cuadriculada
    col_w = pdf.w / len(cols) - 1
    row_h = pdf.font_size * 1.5
    for header in cols:
        pdf.cell(col_w, row_h, header, border=1, align="C")
    pdf.ln(row_h)
    for _, row in sub_df.iterrows():
        for item in row:
            pdf.cell(col_w, row_h, str(item), border=1, align="C")
        pdf.ln(row_h)

    # Firma
    pdf.ln(10)
    pdf.cell(0, 8, "Recibe: ______________", ln=True)
    pdf.cell(0, 8, "Firma: __________________________", ln=True)

    out_path = filepath.with_suffix(f"_{mode}.pdf")
    pdf.output(str(out_path))
    logging.info(f"PDF generado en {out_path}")
    return out_path


def _print_windows(pdf_path: Path):
    """
    Imprime usando COM en Windows.
    """
    pythoncom.CoInitialize()
    try:
        word = Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(pdf_path.resolve()))
        doc.PrintOut()
        doc.Close(False)
        word.Quit()
    finally:
        pythoncom.CoUninitialize()


def _print_cups(pdf_path: Path):
    """
    Imprime usando CUPS en Linux/otros.
    """
    conn = cups.Connection()
    printer_name = conn.getDefault()
    if not printer_name:
        raise RuntimeError("No hay impresora por defecto configurada en CUPS.")
    conn.printFile(printer_name, str(pdf_path), pdf_path.name, {})

# --------------------------------------
# Función de logging genérico
# --------------------------------------
import inspect
import os

def log_evento(mensaje: str, nivel: str = "info"):
    """
    Guarda logs con nombre dinámico según el archivo que llamó.
    """
    frame = inspect.stack()[1]
    caller = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{caller}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve()) for h in logger.handlers):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    level_fn = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical
    }.get(nivel.lower(), logger.info)
    level_fn(mensaje)
