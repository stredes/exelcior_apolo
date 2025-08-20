# app/printer/printer_etiquetas.py
# Generación e impresión de etiquetas desde plantilla Excel.
# - Windows: intenta Excel COM; si falla, usa LibreOffice (soffice).
# - Linux/macOS: usa LibreOffice (soffice) o 'lp' como fallback.

from __future__ import annotations

import os
import platform
import shutil
import subprocess as sp
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, Dict

import openpyxl
import pandas as pd
from app.core.logger_eventos import log_evento

# ----------------- Imports condicionales (Windows) -----------------
try:
    if platform.system() == "Windows":
        import pythoncom  # pywin32
        from win32com.client import Dispatch  # type: ignore
    else:
        pythoncom = None  # type: ignore
        Dispatch = None   # type: ignore
except Exception:  # por seguridad
    pythoncom = None  # type: ignore
    Dispatch = None   # type: ignore

# ----------------- Constantes / Config -----------------
PLANTILLA_PATH = Path("data/etiqueta pedido.xlsx")
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Mapa de celdas por campo
CELDAS_MAP: Dict[str, str] = {
    "rut": "B2",
    "razsoc": "B3",
    "dir": "B4",
    "comuna": "B5",
    "ciudad": "B6",
    "guia": "B7",
    "bultos": "B8",
    "transporte": "B9",
}

# Impresora por defecto (puedes sobreescribir con EXCELCIOR_PRINTER)
DEFAULT_PRINTER = os.environ.get("EXCELCIOR_PRINTER", "Default")

# Timeout en segundos para procesos de impresión (LibreOffice)
PRINT_TIMEOUT_S = int(os.environ.get("EXCELCIOR_PRINT_TIMEOUT", "25"))

# Ejecutable forzado opcional (ruta a soffice)
FORCED_PRINT_APP = os.environ.get("EXCELCIOR_PRINT_APP", "").strip().strip('"')

# ----------------- Utilidades -----------------
def _ensure_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

def _find_soffice() -> Optional[str]:
    """
    Devuelve ruta a 'soffice' si está disponible. Busca en:
    - PATH
    - Rutas típicas de Windows
    - Registro de LibreOffice en Windows
    """
    from shutil import which

    # 1) PATH
    exe = which("soffice") or which("libreoffice")
    if exe:
        return exe

    # 2) Windows: rutas típicas
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\Program Files\LibreOffice\program\soffice.COM",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.COM",
    ]
    for c in candidates:
        if Path(c).exists():
            return c

    # 3) Windows: Registro
    if platform.system() == "Windows":
        try:
            import winreg  # type: ignore

            reg_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LibreOffice\UNO\InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\LibreOffice\UNO\InstallPath"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\LibreOffice\UNO\InstallPath"),
            ]
            for hive, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hive, subkey) as k:
                        val, _ = winreg.QueryValueEx(k, "")
                        exe = Path(val) / "program" / "soffice.exe"
                        if exe.exists():
                            return str(exe)
                        com = Path(val) / "program" / "soffice.COM"
                        if com.exists():
                            return str(com)
                except FileNotFoundError:
                    continue
        except Exception:
            pass

    return None

def _run_cmd(cmd: list[str], timeout_s: int = PRINT_TIMEOUT_S) -> None:
    """Ejecuta un comando con timeout, loguea stdout/stderr y lanza error si rc != 0."""
    creationflags = 0
    startupinfo = None
    if platform.system() == "Windows":
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        startupinfo = sp.STARTUPINFO()
        startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW

    log_evento(f"Ejecutando: {' '.join(cmd)}", "info")
    try:
        proc = sp.Popen(
            cmd,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            text=True,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except sp.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            log_evento(f"⏳ Timeout ({timeout_s}s). stderr: {stderr.strip()[:400]}", "error")
            raise RuntimeError(f"Tiempo de espera excedido ({timeout_s}s) ejecutando impresión.")

        if stdout:
            log_evento(stdout.strip()[:400], "debug")
        if proc.returncode != 0:
            log_evento(f"Comando falló ({proc.returncode}). stderr: {str(stderr).strip()[:400]}", "error")
            raise RuntimeError(f"Error al ejecutar impresión (rc={proc.returncode}).")
    except FileNotFoundError as e:
        raise RuntimeError(f"No se encontró ejecutable: {cmd[0]}") from e

# ----------------- Generación de etiqueta -----------------
def generar_etiqueta_excel(data: dict, output_path: Path) -> Path:
    """
    Copia la plantilla, escribe datos en celdas mapeadas y guarda en output_path.
    Devuelve la ruta final generada.
    """
    try:
        _ensure_exists(PLANTILLA_PATH)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PLANTILLA_PATH, output_path)

        wb = openpyxl.load_workbook(output_path)
        ws = wb.active

        for campo, celda in CELDAS_MAP.items():
            ws[celda] = data.get(campo, "")

        # Formato de página mínimo (opcional)
        try:
            ws.page_setup.orientation = "portrait"
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 1
        except Exception:
            pass

        wb.save(output_path)
        log_evento(f"📄 Etiqueta generada en: {output_path}", "info")
        return output_path

    except Exception as e:
        log_evento(f"❌ Error al generar etiqueta Excel: {e}", "error")
        raise RuntimeError(f"Error al generar etiqueta: {e}")

# ----------------- Impresión -----------------
def _imprimir_excel_windows_via_com(xlsx_path: Path, impresora: str) -> None:
    """Intenta imprimir con Excel COM en Windows."""
    if pythoncom is None or Dispatch is None:
        raise RuntimeError("COM/pywin32 no disponible en este sistema.")

    try:
        pythoncom.CoInitialize()
        excel = None
        wb = None
        try:
            excel = Dispatch("Excel.Application")
            excel.Visible = False
            wb = excel.Workbooks.Open(str(xlsx_path.resolve()))
            hoja = wb.Sheets(1)

            hoja.PageSetup.Zoom = False
            hoja.PageSetup.FitToPagesWide = 1
            hoja.PageSetup.FitToPagesTall = 1

            if impresora:
                excel.ActivePrinter = impresora
            hoja.PrintOut()

            wb.Close(False)
            log_evento(f"🖨️ Enviado por Excel COM: {xlsx_path.name} -> {impresora or '[predeterminada]'}", "info")
        finally:
            try:
                if wb:
                    wb.Close(False)
            except Exception:
                pass
            try:
                if excel:
                    excel.Quit()
            except Exception:
                pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    except Exception as e:
        raise RuntimeError(f"Excel COM falló: {e}")

def _imprimir_via_soffice(xlsx_path: Path, impresora: str) -> None:
    """
    Imprime con LibreOffice (soffice).
    Flags silenciosas para evitar diálogos.
    """
    app = FORCED_PRINT_APP or _find_soffice()
    if not app:
        raise RuntimeError("No se encontró LibreOffice (soffice). Instálalo o define EXCELCIOR_PRINT_APP.")

    # Normalizar .COM -> .exe si existe al lado (Windows)
    app_path = Path(app)
    if app_path.name.lower().endswith(".com"):
        exe_candidate = app_path.with_suffix(".exe")
        if exe_candidate.exists():
            app = str(exe_candidate)

    cmd = [
        app,
        "--headless",
        "--invisible",
        "--norestore",
        "--nolockcheck",
        "--nodefault",
        "--nologo",
        "--nofirststartwizard",
        "--pt", impresora or DEFAULT_PRINTER,
        str(xlsx_path.resolve()),
    ]
    _run_cmd(cmd, timeout_s=PRINT_TIMEOUT_S)
    log_evento(f"🖨️ Enviado a impresora (soffice): {xlsx_path.name} -> {impresora or DEFAULT_PRINTER}", "info")

def _imprimir_via_lp(xlsx_path: Path) -> None:
    """Fallback básico en Linux/macOS usando 'lp' (requerirá asociación/driver)."""
    cmd = ["lp", str(xlsx_path.resolve())]
    _run_cmd(cmd, timeout_s=PRINT_TIMEOUT_S)
    log_evento(f"🖨️ Enviado a impresora (lp): {xlsx_path.name}", "info")

def imprimir_excel(path: Path, impresora: Optional[str] = None) -> None:
    """
    Envia el .xlsx a imprimir:
      - Windows: Excel COM -> (fallback) soffice -> (último) asociación 'startfile/print'
      - Linux/macOS: soffice -> (fallback) lp
    """
    _ensure_exists(path)
    so = platform.system()
    printer = impresora or DEFAULT_PRINTER

    if so == "Windows":
        # 1) Excel COM
        try:
            _imprimir_excel_windows_via_com(path, printer)
            return
        except Exception as com_err:
            log_evento(f"Excel COM no disponible o falló: {com_err}", "warning")

        # 2) soffice
        try:
            _imprimir_via_soffice(path, printer)
            return
        except Exception as lo_err:
            log_evento(f"LibreOffice no disponible o falló: {lo_err}", "warning")

        # 3) Último recurso: asociación del sistema
        try:
            os.startfile(str(path), "print")  # type: ignore
            log_evento(f"Impresión por asociación Windows: {path.name}", "info")
            return
        except Exception as e:
            raise RuntimeError(
                "No se pudo imprimir en Windows: COM falló y no se encontró LibreOffice. "
                "Instala Excel o LibreOffice, o define EXCELCIOR_PRINT_APP con la ruta a soffice.exe."
            ) from e

    else:
        # Linux / macOS
        try:
            _imprimir_via_soffice(path, printer)
            return
        except Exception as lo_err:
            log_evento(f"LibreOffice no disponible o falló: {lo_err}", "warning")

        # Fallback a 'lp'
        try:
            _imprimir_via_lp(path)
            return
        except Exception as e:
            raise RuntimeError(
                "No se pudo imprimir en este sistema: LibreOffice y 'lp' fallaron. "
                "Instala LibreOffice o configura CUPS correctamente."
            ) from e

# ----------------- API pública -----------------
def imprimir_etiqueta_desde_formulario(data: dict, impresora: Optional[str] = None) -> None:
    """
    Genera e imprime una única etiqueta con los datos del formulario.
    """
    try:
        with NamedTemporaryFile(delete=False, suffix=".xlsx", dir=TEMP_DIR) as tmp:
            tmp_path = Path(tmp.name)
        generar_etiqueta_excel(data, tmp_path)
        imprimir_excel(tmp_path, impresora or data.get("transporte") or DEFAULT_PRINTER)
        log_evento("✅ Impresión de etiqueta completada correctamente.", "info")
    except Exception as e:
        log_evento(f"❌ Error en impresión de etiqueta: {e}", "error")
        raise RuntimeError(f"Error en impresión de etiqueta: {e}")

def print_etiquetas(file_path, config, df: pd.DataFrame) -> None:
    """
    Imprime una etiqueta por cada fila del DataFrame (cada fila -> una etiqueta).
    Usa archivos temporales distintos para evitar locks.
    """
    try:
        if df is None or df.empty:
            raise ValueError("El DataFrame de etiquetas está vacío.")

        for _, row in df.iterrows():
            data = {
                "rut": row.get("RUT", ""),
                "razsoc": row.get("Razón Social", "") or row.get("Razon Social", ""),
                "dir": row.get("Dirección", "") or row.get("Direccion", ""),
                "comuna": row.get("Comuna", ""),
                "ciudad": row.get("Ciudad", ""),
                "guia": row.get("Guía", "") or row.get("Guia", ""),
                "bultos": row.get("Bultos", ""),
                "transporte": row.get("Transporte", "") or DEFAULT_PRINTER,
            }
            log_evento(f"🧾 Generando etiqueta para: {data}", "info")

            with NamedTemporaryFile(delete=False, suffix=".xlsx", dir=TEMP_DIR) as tmp:
                tmp_path = Path(tmp.name)

            generar_etiqueta_excel(data, tmp_path)
            imprimir_excel(tmp_path, data.get("transporte") or DEFAULT_PRINTER)

        log_evento("✅ Impresión de todas las etiquetas finalizada.", "info")

    except Exception as e:
        log_evento(f"❌ Error en impresión múltiple de etiquetas: {e}", "error")
        raise RuntimeError(f"Error en impresión múltiple de etiquetas: {e}")
