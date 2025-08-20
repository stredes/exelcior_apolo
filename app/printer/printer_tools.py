# app/printer/printer_tools.py
from __future__ import annotations

from typing import Optional

from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


def insertar_bloque_firma_ws(
    ws: "Worksheet",
    incluir_observacion: bool = False,
    texto_observacion: Optional[str] = None,
) -> None:
    """
    Inserta al final de la hoja un bloque con:
      [línea en blanco]
      A: 'Nombre quien recibe:' | B..D: (celdas fusionadas con línea de firma)
      A: 'Firma quien recibe:'  | B..D: (celdas fusionadas con línea de firma)
      [línea en blanco]
      (opcional) A: 'Observación:' | B..D: texto

    - El rango B..D se ajusta a las columnas disponibles (si hay menos de 4 columnas).
    - Aplica borde INFERIOR fino para simular la línea de firma.
    """
    if ws is None:
        return

    ncols = max(1, ws.max_column)
    label_col = 1  # Columna A
    line_start = 2  # B
    line_end = min(4, ncols) if ncols >= 2 else 1  # Hasta D o la última disponible

    # utilidades de estilo
    font_label = Font(name="Segoe UI", size=10, bold=False)
    font_line = Font(name="Segoe UI", size=10)
    align_left = Alignment(horizontal="left", vertical="center")
    align_center = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin")
    bottom_border = Border(bottom=thin)

    def _fusionar_y_linea(row_idx: int, etiqueta: str):
        # Escribe etiqueta en A
        c_label = ws.cell(row=row_idx, column=label_col, value=etiqueta)
        c_label.font = font_label
        c_label.alignment = align_left

        # Si hay al menos columna B...
        if ncols >= 2:
            c1 = ws.cell(row=row_idx, column=line_start)
            c2 = ws.cell(row=row_idx, column=line_end)
            # Fusionar B..D (o hasta la última disponible)
            if line_end > line_start:
                ws.merge_cells(
                    start_row=row_idx, start_column=line_start,
                    end_row=row_idx, end_column=line_end
                )
            # Aplicar borde inferior a cada celda involucrada (para que quede bien en viewers)
            for col in range(line_start, line_end + 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.border = bottom_border
                cell.font = font_line
                cell.alignment = align_center

    # 1) Línea en blanco
    ws.append([])

    # 2) Nombre
    row_nombre = ws.max_row + 1
    ws.append([])  # reserva la fila
    _fusionar_y_linea(row_nombre, "Nombre quien recibe:")

    # 3) Firma
    row_firma = ws.max_row + 1
    ws.append([])
    _fusionar_y_linea(row_firma, "Firma quien recibe:")

    # 4) Línea en blanco
    ws.append([])

    # 5) Observación (opcional)
    if incluir_observacion:
        row_obs = ws.max_row + 1
        ws.append([])
        c_label = ws.cell(row=row_obs, column=label_col, value="Observación:")
        c_label.font = font_label
        c_label.alignment = align_left
        if ncols >= 2:
            c1 = ws.cell(row=row_obs, column=line_start)
            c2 = ws.cell(row=row_obs, column=line_end)
            if line_end > line_start:
                ws.merge_cells(
                    start_row=row_obs, start_column=line_start,
                    end_row=row_obs, end_column=line_end
                )
            c_text = ws.cell(row=row_obs, column=line_start, value=(texto_observacion or ""))
            c_text.font = font_line
            c_text.alignment = align_left
