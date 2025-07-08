import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import platform

from app.core.logger_eventos import log_evento
from app.config.config_manager import load_config, save_config  # ✅ Config centralizada

# Solo importar COM en Windows
if platform.system() == "Windows":
    import pythoncom
    from win32com.client import Dispatch


def validate_file(file_path: str) -> Tuple[bool, str]:
    """
    Valida que el archivo exista y sea de un tipo soportado.
    Retorna (True, "") si es válido, o (False, mensaje de error) si no lo es.
    """
    path = Path(file_path)

    if not path.exists():
        log_evento(f"Archivo no encontrado: {file_path}", "error")
        return False, "El archivo no existe."

    if path.suffix.lower() not in ('.xlsx', '.xls', '.csv'):
        log_evento(f"Formato de archivo no soportado: {file_path}", "warning")
        return False, "Formato de archivo no soportado (.xlsx, .xls, .csv)"

    return True, ""


def load_excel(file_path: str, config: dict, mode: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    """
    Carga un archivo Excel o CSV en un DataFrame, aplicando las filas de inicio desde la configuración.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    engine = {
        ".xlsx": "openpyxl",
        ".xls": "openpyxl",  # Puedes cambiar a 'xlrd' si lo necesitas para .xls antiguos
        ".csv": None
    }.get(ext)

    skiprows = list(range(config.get(mode, {}).get("start_row", 0)))

    try:
        if ext == ".csv":
            df = pd.read_csv(path, skiprows=skiprows, nrows=max_rows)
        else:
            df = pd.read_excel(path, engine=engine, skiprows=skiprows, nrows=max_rows)

        # Limpieza de nombres de columnas
        df.columns = df.columns.str.strip().str.replace('\u200b', '', regex=True)
        log_evento(f"Archivo cargado: {file_path}", "info")
        return df

    except Exception as e:
        log_evento(f"Error al leer archivo: {e}", "error")
        raise


def apply_transformation(df: pd.DataFrame, config: dict, mode: str) -> pd.DataFrame:
    """
    Aplica las transformaciones configuradas: eliminación de columnas, sumatoria, y formato.
    """
    log_evento(f"Transformando datos para modo: {mode}", "info")

    modo_cfg = config.get(mode, {})
    eliminar = modo_cfg.get("eliminar", [])
    sumar = modo_cfg.get("sumar", [])
    mantener = modo_cfg.get("mantener_formato", [])

    # Eliminar columnas
    df.drop(columns=[col for col in eliminar if col in df.columns], errors='ignore', inplace=True)
    log_evento(f"Columnas eliminadas: {eliminar}", "info")

    # Agregar fila de sumatorias si aplica
    if sumar:
        suma = {col: df[col].sum() if col in df.columns else 0 for col in sumar}
        df = pd.concat([df, pd.DataFrame([suma])], ignore_index=True)
        log_evento(f"Columnas sumadas: {sumar}", "info")

    # Mantener formato como texto
    for col in mantener:
        if col in df.columns:
            df[col] = df[col].astype(str)
    log_evento(f"Columnas convertidas a texto: {mantener}", "info")

    return df


def imprimir_excel(filepath: Path, df: pd.DataFrame, mode: str):
    """
    Imprime el DataFrame usando Excel COM en Windows. Inserta título y formatea celdas.
    """
    if platform.system() != "Windows":
        log_evento("Impresión Excel solo disponible en Windows.", "warning")
        raise NotImplementedError("La impresión desde Excel solo está disponible en Windows.")

    if not filepath.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    temp_xlsx = filepath.with_suffix(".temp.xlsx")
    df.to_excel(temp_xlsx, index=False)

    try:
        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(temp_xlsx.resolve()))
        sheet = wb.Sheets(1)

        # Título dinámico por modo
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = {
            "fedex": f"FIN DE DÍA FEDEX - {fecha_actual}",
            "urbano": f"FIN DE DÍA URBANO - {fecha_actual}"
        }.get(mode.lower(), f"LISTADO GENERAL - {fecha_actual}")

        # Insertar título en la primera fila
        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = titulo
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # Centrado

        # Aplicar bordes y centrado a todas las celdas de datos
        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1
                cell.HorizontalAlignment = -4108

        wb.Save()
        wb.Close(SaveChanges=True)
        log_evento(f"Impresión completada: {filepath.name}", "info")

    except Exception as e:
        log_evento(f"Error al imprimir: {e}", "error")
        raise

    finally:
        excel.Quit()
        pythoncom.CoUninitialize()
        if temp_xlsx.exists():
            temp_xlsx.unlink()
