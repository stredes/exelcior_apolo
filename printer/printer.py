from pathlib import Path
from datetime import datetime
import tempfile
from tkinter import messagebox
from reportlab.pdfgen import canvas
import logging

try:
    from win32com.client import Dispatch
except ImportError:
    Dispatch = None

def export_to_pdf(df, parent):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para exportar a PDF.")
        return
    pdf_path = Path(tempfile.gettempdir()) / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    try:
        c = canvas.Canvas(str(pdf_path))
        c.setTitle("Exportación de Datos")
        text = c.beginText(40, 800)
        text.setFont("Helvetica", 10)
        header = " | ".join(list(df.columns))
        text.textLine(header)
        for _, row in df.head(50).iterrows():
            line = " | ".join(str(x) for x in row)
            text.textLine(line)
        c.drawText(text)
        c.save()
        messagebox.showinfo("Exportar a PDF", f"Archivo exportado: {pdf_path}")
        logging.info(f"Exportado a PDF: {pdf_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al exportar a PDF:\n{e}")

def print_document(sheet, mode, config_columns, df):
    try:
        if sheet is None or df is None:
            raise ValueError("No hay hoja de Excel válida para imprimir.")

        # Ajuste de columnas
        sheet.Cells.EntireColumn.AutoFit()

        # Configuración de impresión
        sheet.PageSetup.Orientation = 2  # Horizontal
        sheet.PageSetup.Zoom = False
        sheet.PageSetup.FitToPagesWide = 1
        sheet.PageSetup.FitToPagesTall = False

        # Pie de página con fecha y hora
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.PageSetup.CenterFooter = f"&\"Arial,Bold\"&8 Impreso el: {now}"

        # Formato para masterTrackingNumber si aplica (FedEx)
        if (mode == "fedex" and 
            config_columns.get(mode, {}).get("mantener_formato") and 
            "Tracking Number" in df.columns):
            
            col_idx = list(df.columns).index("Tracking Number") + 1
            sheet.Columns(col_idx).NumberFormat = "@"
            used_rows = sheet.UsedRange.Rows.Count

            for row in range(2, used_rows + 1):
                cell = sheet.Cells(row, col_idx)
                if cell.Value is not None:
                    try:
                        val = cell.Value
                        if isinstance(val, float) and val.is_integer():
                            cell.Value = str(int(val))
                        else:
                            cell.Value = str(val)
                    except Exception:
                        cell.Value = str(cell.Value)

        # Enviar a imprimir
        sheet.PrintOut()

    except Exception as e:
        messagebox.showerror("Error", f"Error al imprimir:\n{e}")
