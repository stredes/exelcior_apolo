# M�dulo: printer_inventario_codigo.py
# Descripci�n: L�gica de impresi�n correspondiente.

# Módulo: printer_inventario_codigo.py
# Descripción: Lógica de impresión de resultados de consulta por código en el módulo de Inventario


from pathlib import Path
from datetime import datetime

from app.core.logger_eventos import log_evento

def imprimir_inventario_por_codigo(filepath: Path, df):
    """
    Imprime desde Excel una consulta filtrada por código de producto.
    El DataFrame debe tener las columnas ya transformadas.
    """
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        
        excel = None  # Eliminado para compatibilidad Linux
        excel.Visible = False
        wb = excel.Workbooks.Open(str(filepath.resolve()))
        sheet = wb.Sheets(1)

        sheet.Cells.EntireColumn.AutoFit()

        fecha = datetime.now().strftime("%d/%m/%Y")
        sheet.Rows("1:1").Insert()
        sheet.Cells(1, 1).Value = f"INVENTARIO POR CÓDIGO - {fecha}"
        sheet.Range(sheet.Cells(1, 1), sheet.Cells(1, df.shape[1])).Merge()
        sheet.Cells(1, 1).Font.Bold = True
        sheet.Cells(1, 1).Font.Size = 12
        sheet.Cells(1, 1).HorizontalAlignment = -4108  # Centrado

        # Bordes
        for row in range(2, df.shape[0] + 2):
            for col in range(1, df.shape[1] + 1):
                cell = sheet.Cells(row, col)
                cell.Borders.LineStyle = 1

        wb.Save()
        wb.Close(SaveChanges=True)
        log_evento(f"Impresión por código completada correctamente: {filepath}", "info")

    except Exception as e:
        log_evento(f"Error en impresión por código: {e}", "error")
        raise RuntimeError(f"Error en impresión por código: {e}")

# Linux compatible version: Use openpyxl or external print handling
