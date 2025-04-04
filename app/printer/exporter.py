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
