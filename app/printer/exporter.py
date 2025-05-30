import subprocess
import pandas as pd
from pathlib import Path
from tkinter import messagebox
from datetime import datetime
import platform

def export_to_pdf(df: pd.DataFrame, parent, imprimir: bool = False):
    """
    Exporta un DataFrame a un archivo Excel (.xlsx) y permite al usuario
    abrirlo o imprimirlo directamente en sistemas Linux (LibreOffice).

    Args:
        df (pd.DataFrame): DataFrame a exportar.
        parent (tk.Widget): Ventana principal de Tkinter.
        imprimir (bool): Si es True, intentará enviar directamente a impresión.
    """
    if df.empty:
        messagebox.showwarning("Exportar", "No hay datos para exportar.")
        return

    try:
        # Crear carpeta de exportaciones si no existe
        export_dir = Path.home() / "exelcior_exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        # Definir nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"listado_exportado_{timestamp}.xlsx"
        export_path = export_dir / filename

        # Exportar a Excel con openpyxl
        df.to_excel(export_path, index=False, engine='openpyxl')

        messagebox.showinfo("Exportación Exitosa", f"Archivo exportado en:\n{export_path}")

        # Si se desea imprimir directamente
        if imprimir and platform.system() == "Linux":
            subprocess.run(["libreoffice", "--headless", "--pt", "Default", str(export_path)], check=False)
        else:
            subprocess.run(["libreoffice", "--calc", str(export_path)], check=False)

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar/imprimir:\n{e}")
