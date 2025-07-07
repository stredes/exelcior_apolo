# Módulo: printer_etiquetas.py
# Descripción: Generación e impresión de etiquetas desde plantilla Excel, usando COM (Windows)

import shutil
import openpyxl
import pythoncom
from win32com.client import Dispatch
from pathlib import Path

from app.core.logger_eventos import log_evento

# Ruta de plantilla y archivo temporal
PLANTILLA_PATH = Path("data/etiqueta pedido.xlsx")
OUTPUT_PATH = Path("temp/etiqueta_impresion.xlsx")

# Celdas asociadas a cada campo
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

DEFAULT_PRINTER = "URBANO"  # Cambiar por nombre de impresora real si es necesario


def generar_etiqueta_excel(data: dict, output_path: Path = OUTPUT_PATH):
    """
    Llena una plantilla Excel con los datos de la etiqueta y la guarda temporalmente.
    """
    try:
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
    Imprime un archivo Excel mediante COM en Windows.
    """
    try:
        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False

        wb = excel.Workbooks.Open(str(path.resolve()))
        hoja = wb.Sheets(1)

        # Configurar escala para impresión
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
    Flujo completo: generación de etiqueta personalizada y envío a impresión.
    """
    try:
        generar_etiqueta_excel(data, OUTPUT_PATH)
        imprimir_excel(OUTPUT_PATH, impresora)
        log_evento("✅ Impresión de etiqueta completada correctamente.", "info")
    except Exception as e:
        raise RuntimeError(f"Error en impresión de etiqueta: {e}")
