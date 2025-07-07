# Módulo: impression_tools.py
# Descripción: Herramientas unificadas para generación de Excel con formato e impresión automática

from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
import platform
import subprocess
import os

from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.core.logger_eventos import log_evento


def generar_excel_temporal(df: pd.DataFrame, titulo: str, sheet_name: str = "Listado") -> Path:
    """
    Genera un archivo Excel temporal con el contenido de un DataFrame,
    incluyendo título centrado, bordes, alineación centrada y formato cuadriculado.
    Devuelve la ruta al archivo generado.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            temp_path = Path(tmp.name)

        # Insertar fila vacía para el título
        df_to_export = pd.DataFrame(columns=df.columns)
        df_to_export.loc[0] = [""] * len(df.columns)
        df_to_export = pd.concat([df_to_export, df], ignore_index=True)

        with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
            df_to_export.to_excel(writer, index=False, sheet_name=sheet_name)
            sheet = writer.book[sheet_name]

            total_columnas = len(df.columns)

            # Título centrado
            sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columnas)
            title_cell = sheet.cell(row=1, column=1)
            title_cell.value = titulo
            title_cell.font = Font(bold=True, size=12)
            title_cell.alignment = Alignment(horizontal="center")

            # Estilo general de celdas
            borde_fino = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )

            for col_idx in range(1, total_columnas + 1):
                col_letter = get_column_letter(col_idx)
                sheet.column_dimensions[col_letter].auto_size = True  # Ignorado por LibreOffice

            for row in sheet.iter_rows(min_row=2, max_row=df.shape[0] + 2, min_col=1, max_col=total_columnas):
                for cell in row:
                    cell.alignment = Alignment(horizontal="center")
                    cell.border = borde_fino

        log_evento(f"📄 Archivo Excel temporal generado: {temp_path}", "info")
        return temp_path

    except Exception as e:
        log_evento(f"❌ Error al generar archivo Excel temporal: {e}", "error")
        raise RuntimeError(f"Error al generar Excel temporal: {e}")


def enviar_a_impresora(file_path: Path):
    """
    Envía el archivo Excel indicado a la impresora predeterminada según el sistema operativo.
    """
    sistema = platform.system()
    try:
        if sistema == "Windows":
            os.startfile(str(file_path), "print")
        elif sistema == "Linux":
            subprocess.run(["libreoffice", "--headless", "--pt", "Default", str(file_path)], check=True)
        elif sistema == "Darwin":
            subprocess.run(["lp", str(file_path)], check=True)
        else:
            raise OSError("Sistema operativo no compatible para impresión automática.")

        log_evento(f"🖨️ Archivo enviado a la impresora: {file_path}", "info")

    except Exception as e:
        log_evento(f"❌ Error al imprimir archivo: {e}", "error")
        raise RuntimeError(f"Error al imprimir archivo: {e}")
