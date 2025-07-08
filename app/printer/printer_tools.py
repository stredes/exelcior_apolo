# app/printer/printer_tools.py
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment

def agregar_nombre_firma(ws, fila_inicio: int, observacion: str = ""):
    """
    Inserta una sección de nombre y firma en la hoja de cálculo.
    """
    ws.append([])
    ws.append(["Nombre quien recibe:", "___________________________"])
    ws.append(["Firma quien recibe:", "___________________________"])
    ws.append([])
    if observacion:
        ws.append(["Observación:", observacion])
    for row in ws.iter_rows(min_row=fila_inicio + 1, max_row=ws.max_row):
        for cell in row:
            cell.font = Font(name='Segoe UI', size=10)
            cell.alignment = Alignment(horizontal='left')
