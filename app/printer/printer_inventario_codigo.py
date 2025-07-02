from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
import os
import platform
import subprocess

from app.core.logger_eventos import log_evento

def print_inventario_codigo(df: pd.DataFrame):
    """
    Imprime una consulta filtrada por código desde un DataFrame.
    Genera un archivo temporal Excel con formato y lo envía a la impresora por sistema operativo.
    """
    try:
        # Crear archivo temporal Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            temp_path = Path(tmp.name)

        fecha = datetime.now().strftime("%d/%m/%Y")
        titulo = f"INVENTARIO POR CÓDIGO - {fecha}"

        # Insertar título y exportar
        df_to_export = pd.DataFrame(columns=df.columns)
        df_to_export.loc[0] = [""] * len(df.columns)  # Fila vacía para título
        df_to_export = pd.concat([df_to_export, df], ignore_index=True)
        with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
            df_to_export.to_excel(writer, index=False, sheet_name="Inventario")
            sheet = writer.book["Inventario"]
            sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
            cell = sheet.cell(row=1, column=1)
            cell.value = titulo
            cell.font = cell.font.copy(bold=True, size=12)
            cell.alignment = cell.alignment.copy(horizontal="center")

        log_evento(f"Archivo temporal generado para impresión por código: {temp_path}", "info")

        # Enviar a impresión por sistema operativo
        _print_excel(temp_path)

        log_evento("Impresión por código completada correctamente.", "info")

    except Exception as e:
        log_evento(f"Error en impresión por código: {e}", "error")
        raise RuntimeError(f"Error al imprimir inventario por código: {e}")

def _print_excel(file_path: Path):
    """
    Imprime un archivo Excel en función del sistema operativo.
    """
    system = platform.system()
    if system == "Windows":
        os.startfile(str(file_path), "print")
    elif system == "Linux":
        subprocess.run(["libreoffice", "--headless", "--pt", "Default", str(file_path)], check=False)
    elif system == "Darwin":  # macOS
        subprocess.run(["lp", str(file_path)], check=False)
    else:
        raise OSError("Sistema operativo no compatible para impresión automática.")
