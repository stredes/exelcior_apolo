import pandas as pd
from pathlib import Path
import openpyxl
import pythoncom
from win32com.client import Dispatch
import logging

def generar_archivo_etiquetas(df: pd.DataFrame, output_path: Path):
    """
    Genera un archivo Excel con formato tipo etiqueta (una etiqueta por página).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Etiqueta"

    columnas = df.columns.tolist()
    for row in df.itertuples(index=False):
        for col, val in zip(columnas, row):
            ws.append([f"{col}: {val}"])
        ws.append(["Guía: " + str(row[0])])  # Guía al final si deseas
        ws.append([""])  # Espacio entre etiquetas

    wb.save(output_path)

def imprimir_archivo_excel(ruta_archivo: Path, impresora: str = "URBANO"):
    """
    Imprime el archivo Excel en la impresora especificada de forma silenciosa.
    """
    try:
        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False

        wb = excel.Workbooks.Open(str(ruta_archivo.resolve()))
        hoja = wb.Sheets(1)
        hoja.Columns.AutoFit()

        excel.ActivePrinter = impresora
        hoja.PrintOut()

        wb.Close(SaveChanges=False)
        excel.Quit()
    except Exception as e:
        logging.error(f"Error al imprimir etiquetas: {e}")
        raise

def print_etiquetas(_, config_columns: dict, df: pd.DataFrame):
    """
    Punto de entrada para impresión de etiquetas desde el sistema.
    """
    try:
        temp_path = Path("temp_etiquetas.xlsx")
        generar_archivo_etiquetas(df, temp_path)
        imprimir_archivo_excel(temp_path, impresora="URBANO")
    except Exception as e:
        logging.error(f"No se pudo imprimir etiquetas: {e}")
