import shutil
import openpyxl
import pythoncom
from win32com.client import Dispatch
from pathlib import Path

# Rutas
PLANTILLA_PATH = Path("data/etiqueta pedido.xlsx")
OUTPUT_PATH = Path("temp/etiqueta_impresion.xlsx")  # temporal

# Mapeo de datos a celdas
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

DEFAULT_PRINTER = "URBANO"  # puedes cambiarlo por otro

def generar_etiqueta_excel(data: dict, output_path: Path):
    """
    Llena la plantilla Excel con los datos de la etiqueta.
    """
    shutil.copy(PLANTILLA_PATH, output_path)
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active

    for campo, celda in CELDAS_MAP.items():
        ws[celda] = data.get(campo, "")

    wb.save(output_path)

def imprimir_excel(path: Path, impresora: str = DEFAULT_PRINTER):
    """
    Imprime el archivo Excel usando COM (solo Windows).
    """
    pythoncom.CoInitialize()
    excel = Dispatch("Excel.Application")
    excel.Visible = False
    libro = excel.Workbooks.Open(str(path.resolve()))
    hoja = libro.Sheets(1)
    hoja.PageSetup.Zoom = False
    hoja.PageSetup.FitToPagesWide = 1
    hoja.PageSetup.FitToPagesTall = 1
    excel.ActivePrinter = impresora
    hoja.PrintOut()
    libro.Close(False)
    excel.Quit()

def imprimir_etiqueta_desde_formulario(data: dict, impresora: str = DEFAULT_PRINTER):
    """
    Flujo completo: generar archivo y enviarlo a impresión.
    """
    generar_etiqueta_excel(data, OUTPUT_PATH)
    imprimir_excel(OUTPUT_PATH, impresora)
