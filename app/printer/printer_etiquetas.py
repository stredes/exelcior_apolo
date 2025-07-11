# Módulo: printer_etiquetas.py
# Descripción: Generación e impresión de etiquetas desde plantilla Excel, usando COM (Windows)

import shutil
import openpyxl
import pythoncom
from win32com.client import Dispatch
from pathlib import Path
import pandas as pd
import os

from app.core.logger_eventos import log_evento

# Rutas de plantilla y archivo temporal
PLANTILLA_PATH = Path("data/etiqueta pedido.xlsx")
OUTPUT_PATH = Path("temp/etiqueta_impresion.xlsx")

# Asegurar carpeta temporal
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Mapa de celdas por campo
CELDAS_MAP = {
    "rut": "B2",
    "razsoc": "B3",
    "dir": "B4",
    "comuna": "B5",
    "ciudad": "B6",
    "guia": "B7",
    "bultos": "B8",
    "transporte": "B9"
}

# Impresora predeterminada
DEFAULT_PRINTER = "URBANO"


def generar_etiqueta_excel(data: dict, output_path: Path = OUTPUT_PATH):
    """
    Copia la plantilla, escribe los datos en las celdas mapeadas y guarda en output_path.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)  # Asegurar directorio
        shutil.copy(PLANTILLA_PATH, output_path)

        wb = openpyxl.load_workbook(output_path)
        ws = wb.active

        for campo, celda in CELDAS_MAP.items():
            ws[celda] = data.get(campo, "")

        wb.save(output_path)
        log_evento(f"📄 Etiqueta generada en: {output_path}", "info")

    except Exception as e:
        log_evento(f"❌ Error al generar etiqueta Excel: {e}", "error")
        raise RuntimeError(f"Error al generar etiqueta: {e}")


def imprimir_excel(path: Path, impresora: str = DEFAULT_PRINTER):
    """
    Usa COM para abrir el archivo con Excel y enviarlo a la impresora predeterminada.
    """
    try:
        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False

        wb = excel.Workbooks.Open(str(path.resolve()))
        hoja = wb.Sheets(1)

        hoja.PageSetup.Zoom = False
        hoja.PageSetup.FitToPagesWide = 1
        hoja.PageSetup.FitToPagesTall = 1

        excel.ActivePrinter = impresora
        hoja.PrintOut()

        wb.Close(False)
        excel.Quit()

        log_evento(f"🖨️ Archivo enviado a impresión: {path} -> {impresora}", "info")

    except Exception as e:
        log_evento(f"❌ Error al imprimir etiqueta: {e}", "error")
        raise RuntimeError(f"Error al imprimir archivo: {e}")


def imprimir_etiqueta_desde_formulario(data: dict, impresora: str = DEFAULT_PRINTER):
    """
    Imprime una única etiqueta desde los datos ingresados por formulario.
    """
    try:
        generar_etiqueta_excel(data, OUTPUT_PATH)
        imprimir_excel(OUTPUT_PATH, impresora)
        log_evento("✅ Impresión de etiqueta completada correctamente.", "info")
    except Exception as e:
        raise RuntimeError(f"Error en impresión de etiqueta: {e}")


def print_etiquetas(file_path, config, df: pd.DataFrame):
    """
    Imprime una etiqueta por cada fila del DataFrame proporcionado.
    """
    try:
        if df.empty:
            raise ValueError("El DataFrame de etiquetas está vacío.")

        for _, row in df.iterrows():
            data = {
                "rut": row.get("RUT", ""),
                "razsoc": row.get("Razón Social", ""),
                "dir": row.get("Dirección", ""),
                "comuna": row.get("Comuna", ""),
                "ciudad": row.get("Ciudad", ""),
                "guia": row.get("Guía", ""),
                "bultos": row.get("Bultos", ""),
                "transporte": row.get("Transporte", DEFAULT_PRINTER)
            }
            log_evento(f"🧾 Generando etiqueta para: {data}", "info")
            generar_etiqueta_excel(data)
            imprimir_excel(OUTPUT_PATH, data["transporte"])

        log_evento("✅ Impresión de todas las etiquetas finalizada.", "info")

    except Exception as e:
        log_evento(f"❌ Error en impresión múltiple de etiquetas: {e}", "error")
        raise RuntimeError(f"Error en impresión múltiple de etiquetas: {e}")
