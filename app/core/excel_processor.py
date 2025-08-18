import unicodedata
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from datetime import datetime
import platform

from app.core.logger_eventos import log_evento
# ✅ Fuente única de configuración
from app.config.config_manager import (
    load_config,
    save_config,  # mantenido si lo usas en otra parte
    get_start_row,
    get_effective_mode_rules,
)

# Solo importar COM en Windows
if platform.system() == "Windows":
    import pythoncom
    from win32com.client import Dispatch


# ==========================
# Utilidades de normalización
# ==========================

_ZWSP = "\u200b"  # zero-width space

def _normalize_name(s: str) -> str:
    """
    Normaliza nombres de columnas para comparaciones robustas:
    - quita invisibles, tildes, colapsa espacios
    - unifica variantes de 'Nº/N°/No./Nro.'
    - lower()
    """
    if s is None:
        return ""
    s = str(s).replace(_ZWSP, "")
    s = " ".join(s.strip().split())
    s_nfkd = unicodedata.normalize("NFKD", s)
    s_no_accents = "".join(ch for ch in s_nfkd if not unicodedata.combining(ch))
    s_equiv = (
        s_no_accents
        .replace("Nº", "N")
        .replace("N°", "N")
        .replace("No.", "N")
        .replace("No ", "N ")
        .replace("Nro.", "N")
        .replace("Nro ", "N ")
    )
    return s_equiv.lower()


def _build_column_map(columns: List[str]) -> Dict[str, str]:
    """
    Crea un mapa {nombre_normalizado: nombre_real} de las columnas del DF.
    """
    return {_normalize_name(c): c for c in columns}


# ==========================
# Validación de archivo
# ==========================

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


# ==========================
# Carga de Excel con config
# ==========================

def load_excel(file_path: str, config: dict, mode: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    """
    Carga un archivo Excel o CSV en un DataFrame, aplicando las filas de inicio desde la configuración efectiva.
    También limpia nombres de columnas visibles (strip, colapsa espacios, quita ZWSP).
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    engine = {
        ".xlsx": "openpyxl",
        ".xls": "openpyxl",  # usa xlrd si lo necesitas para .xls antiguos
        ".csv": None
    }.get(ext)

    # ✅ Usa la fuente única para obtener start_row
    start_row = get_start_row(mode, config)
    skiprows = list(range(start_row)) if start_row and start_row > 0 else None

    try:
        if ext == ".csv":
            df = pd.read_csv(path, skiprows=skiprows, nrows=max_rows)
        else:
            df = pd.read_excel(path, engine=engine, skiprows=skiprows, nrows=max_rows)

        # Limpieza de nombres de columnas visibles
        df.columns = (
            pd.Index(df.columns)
              .map(lambda c: str(c).replace(_ZWSP, ""))
              .map(lambda c: " ".join(c.strip().split()))
        )
        log_evento(f"Archivo cargado: {file_path}", "info")
        return df

    except Exception as e:
        log_evento(f"Error al leer archivo: {e}", "error")
        raise


# ==========================
# Transformación según config
# ==========================

def apply_transformation(df: pd.DataFrame, config: dict, mode: str) -> pd.DataFrame:
    """
    Aplica las transformaciones configuradas: eliminación de columnas, sumatoria, y formato.
    Usa matching tolerante (normalización) para resolver columnas de config vs columnas reales.
    """
    log_evento(f"Transformando datos para modo: {mode}", "info")

    # ✅ Reglas efectivas del modo (misma fuente que usa todo el sistema)
    rules = get_effective_mode_rules(mode, config)
    eliminar = list(rules.get("eliminar", []) or [])
    sumar = list(rules.get("sumar", []) or [])
    mantener = list(rules.get("mantener_formato", []) or [])

    # Construye el mapa normalizado de columnas reales
    colmap = _build_column_map(list(df.columns))

    def resolve_targets(targets: List[str]) -> List[str]:
        resolved: List[str] = []
        misses: List[str] = []
        for t in targets:
            key = _normalize_name(t)
            real = colmap.get(key)
            if real is not None:
                resolved.append(real)
            else:
                misses.append(t)
        if resolved:
            log_evento(f"[XFORM] Match columnas -> {targets} => {resolved}", "info")
        if misses:
            log_evento(f"[XFORM] No encontradas en DF (tras normalizar): {misses}", "warning")
        return resolved

    eliminar_resolved = resolve_targets(eliminar)
    sumar_resolved = resolve_targets(sumar)
    mantener_resolved = resolve_targets(mantener)

    df2 = df.copy()

    # 1) Eliminar columnas
    if eliminar_resolved:
        df2.drop(columns=[c for c in eliminar_resolved if c in df2.columns], errors='ignore', inplace=True)
        log_evento(f"Columnas eliminadas: {eliminar_resolved}", "info")
    else:
        log_evento("Columnas eliminadas: []", "info")

    # 2) Sumatorias (conversión a numérico segura)
    if sumar_resolved:
        for col in sumar_resolved:
            if col in df2.columns:
                df2[col] = pd.to_numeric(df2[col], errors="coerce")
        suma = {col: (df2[col].sum() if col in df2.columns else 0) for col in sumar_resolved}
        df2 = pd.concat([df2, pd.DataFrame([suma])], ignore_index=True)
        log_evento(f"[XFORM] Fila de sumatoria creada: {suma}", "info")

    # 3) Mantener formato como texto
    if mantener_resolved:
        for col in mantener_resolved:
            if col in df2.columns:
                df2[col] = df2[col].astype(str)
        log_evento(f"Columnas convertidas a texto: {mantener_resolved}", "info")
    else:
        log_evento("Columnas convertidas a texto: []", "info")

    return df2


# ==========================
# Impresión por Excel COM
# ==========================

def imprimir_excel(filepath: Path, df: pd.DataFrame, mode: str):
    """
    Imprime el DataFrame usando Excel COM en Windows. Inserta título y formatea celdas.
    Asegura orientación horizontal (Landscape) y ajuste a 1 página de ancho.
    """
    if platform.system() != "Windows":
        log_evento("Impresión Excel solo disponible en Windows.", "warning")
        raise NotImplementedError("La impresión desde Excel solo está disponible en Windows.")

    if not filepath.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    temp_xlsx = filepath.with_suffix(".temp.xlsx")
    df.to_excel(temp_xlsx, index=False)

    excel = None
    wb = None
    try:
        pythoncom.CoInitialize()
        excel = Dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(temp_xlsx.resolve()))
        sh = wb.Worksheets(1)

        # Título dinámico por modo
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulo = {
            "fedex": f"FIN DE DÍA FEDEX - {fecha_actual}",
            "urbano": f"FIN DE DÍA URBANO - {fecha_actual}"
        }.get(mode.lower(), f"LISTADO GENERAL - {fecha_actual}")

        # Insertar título en la primera fila
        sh.Rows("1:1").Insert()
        sh.Cells(1, 1).Value = titulo
        sh.Range(sh.Cells(1, 1), sh.Cells(1, max(1, df.shape[1]))).Merge()
        sh.Cells(1, 1).Font.Bold = True
        sh.Cells(1, 1).Font.Size = 12
        sh.Cells(1, 1).HorizontalAlignment = -4108  # xlCenter

        # Dar formato a rango usado (bordes + centrado + autofit)
        used = sh.UsedRange
        used.Borders.LineStyle = 1            # xlContinuous
        used.HorizontalAlignment = -4108      # xlCenter
        used.VerticalAlignment = -4108        # xlCenter
        used.Columns.AutoFit()

        # ✅ Configurar página: horizontal y ajustar a 1 página de ancho
        sh.PageSetup.Orientation = 2          # xlLandscape
        sh.PageSetup.Zoom = False
        sh.PageSetup.FitToPagesWide = 1
        sh.PageSetup.FitToPagesTall = False   # tantas páginas de alto como necesite

        # Imprimir
        sh.PrintOut()
        wb.Close(SaveChanges=False)
        log_evento(f"Impresión completada: {filepath.name}", "info")

    except Exception as e:
        log_evento(f"Error al imprimir: {e}", "error")
        try:
            if wb:
                wb.Close(SaveChanges=False)
        except Exception:
            pass
        raise
    finally:
        try:
            if excel:
                excel.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        try:
            if temp_xlsx.exists():
                temp_xlsx.unlink()
        except Exception:
            pass
