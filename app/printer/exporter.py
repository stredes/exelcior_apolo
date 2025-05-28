from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import os

from app.core.logger_eventos import log_evento  # ✅ integración de logging


def export_to_pdf(df, parent_window, filename="reporte"):
    try:
        if df is None or df.empty:
            log_evento("No se pudo exportar: DataFrame vacío o nulo", "warning")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)

        col_width = 190 / len(df.columns)

        # Encabezado
        pdf.set_fill_color(200, 200, 200)
        for col in df.columns:
            pdf.cell(col_width, 10, str(col), border=1, ln=0, align="C", fill=True)
        pdf.ln()

        # Filas
        for _, row in df.iterrows():
            for value in row:
                pdf.cell(col_width, 10, str(value), border=1, ln=0, align="C")
            pdf.ln()

        # Pie de página
        pdf.set_y(-15)
        pdf.set_font("Arial", size=8)
        pdf.cell(0, 10, f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 0, 'C')

        output_dir = Path("exportados/pdf")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        pdf.output(str(output_file))

        log_evento(f"PDF generado correctamente: {output_file}", "info")

    except Exception as e:
        log_evento(f"Error al exportar PDF: {e}", "error")
