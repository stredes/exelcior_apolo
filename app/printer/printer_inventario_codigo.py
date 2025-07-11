# Módulo: printer_inventario_codigo.py
# Descripción: Impresión automática del inventario filtrado por código, compatible con printer_map

from pathlib import Path
from datetime import datetime
import pandas as pd
import os
import platform
import subprocess

from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, Border, Side

from app.core.logger_eventos import log_evento

TEMP_PATH = Path("temp/inventario_codigo.xlsx")
TEMP_PATH.parent.mkdir(parents=True, exist_ok=True)  # Asegurar carpeta temp


def print_inventario_codigo(file_path, config, df: pd.DataFrame):
    """
    Entrada estandarizada desde printer_map. Imprime un Excel con formato a partir de un DataFrame.
    """
    try:
        if df.empty:
            raise ValueError("El DataFrame del inventario por código está vacío.")

        fecha = datetime.now().strftime("%d/%m/%Y")
        titulo = f"INVENTARIO POR CÓDIGO - {fecha}"

        # Insertar fila vacía para el título
        df_to_export = pd.DataFrame(columns=df.columns)
        df_to_export.loc[0] = [""] * len(df.columns)
        df_to_export = pd.concat([df_to_export, df], ignore_index=True)

        # Exportar a Excel con estilos
        with pd.ExcelWriter(TEMP_PATH, engine="openpyxl") as writer:
            df_to_export.to_excel(writer, index=False, sheet_name="Inventario")
            sheet = writer.book["Inventario"]

            total_columnas = len(df.columns)
            sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columnas)

            # Título
            cell = sheet.cell(row=1, column=1)
            cell.value = titulo
            cell.font = Font(bold=True, size=12)
            cell.alignment = Alignment(horizontal="center")

            # Bordes y alineación
            borde_fino = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            for col_idx in range(1, total_columnas + 1):
                col_letter = get_column_letter(col_idx)
                sheet.column_dimensions[col_letter].auto_size = True  # Placeholder (Excel-only)

            for row in sheet.iter_rows(min_row=2, max_row=df.shape[0] + 2, min_col=1, max_col=total_columnas):
                for cell in row:
                    cell.alignment = Alignment(horizontal="center")
                    cell.border = borde_fino

        log_evento(f"📄 Archivo temporal generado para impresión por código: {TEMP_PATH}", "info")
        _enviar_a_impresora(TEMP_PATH)
        log_evento("✅ Impresión de inventario por código completada correctamente.", "info")

    except Exception as e:
        log_evento(f"❌ Error en impresión por código: {e}", "error")
        raise RuntimeError(f"Error al imprimir inventario por código: {e}")


def _enviar_a_impresora(file_path: Path):
    """
    Imprime un archivo Excel dependiendo del sistema operativo.
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
    except Exception as e:
        log_evento(f"❌ Error al imprimir archivo Excel: {e}", "error")
        raise RuntimeError(f"Error al enviar a impresora: {e}")
