import platform
import tempfile
import subprocess
import pandas as pd
from pathlib import Path

def imprimir_inventario_excel(df: pd.DataFrame):
    if df.empty:
        raise ValueError("DataFrame está vacío. Nada que imprimir.")

    # Crear archivo temporal Excel
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        filepath = Path(tmp.name)
        df.to_excel(filepath, index=False)

    sistema = platform.system()
    if sistema == "Windows":
        _imprimir_en_windows(filepath)
    elif sistema == "Linux":
        _imprimir_en_linux(filepath)
    else:
        raise NotImplementedError(f"Impresión no implementada para {sistema}")

def _imprimir_en_windows(filepath: Path):
    try:
        import pythoncom
        from win32com.client import Dispatch

        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath))
        sheet = wb.Sheets(1)
        sheet.Columns.AutoFit()
        wb.PrintOut()
        wb.Close(False)
        excel.Quit()
    except Exception as e:
        raise RuntimeError(f"Error al imprimir en Windows: {e}")

def _imprimir_en_linux(filepath: Path):
    try:
        subprocess.run(
            ["libreoffice", "--headless", "--pt", "default", str(filepath)],
            check=True
        )
    except Exception as e:
        raise RuntimeError(f"Error al imprimir en Linux: {e}")
