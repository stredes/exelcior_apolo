from fpdf import FPDF
import tempfile
from datetime import datetime
from pathlib import Path
import os

def export_to_pdf(df, parent_window, filename="reporte"):
    if df is None or df.empty:
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    col_width = 190 / len(df.columns)

    # Escribir encabezado
    pdf.set_fill_color(200, 200, 200)
    for col in df.columns:
        pdf.cell(col_width, 10, str(col), border=1, ln=0, align="C", fill=True)
    pdf.ln()

    # Escribir filas
    for _, row in df.iterrows():
        for value in row:
            pdf.cell(col_width, 10, str(value), border=1, ln=0, align="C")
        pdf.ln()

    # Pie de página con fecha y hora
    pdf.set_y(-15)
    pdf.set_font("Arial", size=8)
    pdf.cell(0, 10, f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 0, 'C')

    # Guardar en carpeta "exportados/pdf/"
    output_dir = Path("exportados/pdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    pdf.output(str(output_file))
    print(f"✅ PDF generado: {output_file}")

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
