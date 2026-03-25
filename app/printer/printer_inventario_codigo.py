# MÃ³dulo: printer_inventario_codigo.py
# DescripciÃ³n: ImpresiÃ³n automÃ¡tica del inventario filtrado por cÃ³digo, compatible con printer_map

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


def print_inventario_codigo(file_path=None, config=None, df: pd.DataFrame = None):
    """
    Entrada estandarizada desde printer_map. Imprime un Excel con formato a partir de un DataFrame.
    Compatible con llamada antigua: print_inventario_codigo(df=...).
    """
    try:
        if isinstance(file_path, pd.DataFrame) and df is None:
            df = file_path
        if df is None:
            raise ValueError("No se recibio DataFrame para impresion de inventario por codigo.")
        if df.empty:
            raise ValueError("El DataFrame del inventario por codigo esta vacio.")

        fecha = datetime.now().strftime("%d/%m/%Y")
        titulo = f"INVENTARIO POR CÃ“DIGO - {fecha}"

        # Insertar fila vacÃ­a para el tÃ­tulo
        df_to_export = pd.DataFrame(columns=df.columns)
        df_to_export.loc[0] = [""] * len(df.columns)
        df_to_export = pd.concat([df_to_export, df], ignore_index=True)

        # Exportar a Excel con estilos
        with pd.ExcelWriter(TEMP_PATH, engine="openpyxl") as writer:
            df_to_export.to_excel(writer, index=False, sheet_name="Inventario")
            sheet = writer.book["Inventario"]

            total_columnas = len(df.columns)
            sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columnas)

            # TÃ­tulo
            cell = sheet.cell(row=1, column=1)
            cell.value = titulo
            cell.font = Font(bold=True, size=12)
            cell.alignment = Alignment(horizontal="center")

            # Bordes y alineaciÃ³n
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

            # Configuracion de impresion: horizontal y ajuste a una sola hoja.
            sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE
            sheet.page_setup.fitToWidth = 1
            sheet.page_setup.fitToHeight = 1
            sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
            sheet.sheet_properties.pageSetUpPr.fitToPage = True
            sheet.page_margins.left = 0.2
            sheet.page_margins.right = 0.2
            sheet.page_margins.top = 0.3
            sheet.page_margins.bottom = 0.3
            sheet.page_margins.header = 0.1
            sheet.page_margins.footer = 0.1
            sheet.print_options.horizontalCentered = True

        log_evento(f"ðŸ“„ Archivo temporal generado para impresiÃ³n por cÃ³digo: {TEMP_PATH}", "info")
        _enviar_a_impresora(TEMP_PATH)
        log_evento("âœ… ImpresiÃ³n de inventario por cÃ³digo completada correctamente.", "info")

    except Exception as e:
        log_evento(f"âŒ Error en impresiÃ³n por cÃ³digo: {e}", "error")
        raise RuntimeError(f"Error al imprimir inventario por cÃ³digo: {e}")


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
            raise OSError("Sistema operativo no compatible para impresiÃ³n automÃ¡tica.")
    except Exception as e:
        log_evento(f"âŒ Error al imprimir archivo Excel: {e}", "error")
        raise RuntimeError(f"Error al enviar a impresora: {e}")

