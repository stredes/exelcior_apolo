# app/printer/printer_tools.py
from __future__ import annotations

from datetime import datetime
from typing import Tuple
import pandas as pd
import numpy as np


# =============== Limpieza y shaping para FEDEX ===============

def _stringify_tracking(series: pd.Series) -> pd.Series:
    """
    Convierte cualquier serie de tracking a string sin notación científica ni '.0'.
    - Si es numérica -> Int64 -> str (conserva todos los dígitos)
    - Si viene como texto -> str.strip()
    """
    if series is None:
        return pd.Series([], dtype="object")

    # Intento 1: convertir a número
    as_num = pd.to_numeric(series, errors="coerce")
    out = pd.Series("", index=series.index, dtype="object")

    # numéricos válidos -> Int64 -> str
    mask_num = as_num.notna()
    if mask_num.any():
        out.loc[mask_num] = as_num.loc[mask_num].astype("Int64").astype(str)

    # el resto -> str normal
    mask_rest = ~mask_num
    if mask_rest.any():
        out.loc[mask_rest] = series.loc[mask_rest].astype(str).str.strip()

    return out


def _normalize_date(series: pd.Series) -> pd.Series:
    """
    Normaliza fechas a 'YYYY-MM-DD'.
    Acepta string ISO, datetime, y serial de Excel (número de días).
    """
    if series is None:
        return pd.Series([], dtype="object")

    # Intento directo
    dt = pd.to_datetime(series, errors="coerce", utc=False)

    # Si quedó NaT (posible serial Excel), reintenta como días desde 1899-12-30
    mask_nat = dt.isna()
    if mask_nat.any():
        as_num = pd.to_numeric(series[mask_nat], errors="coerce")
        mask_num = as_num.notna()
        if mask_num.any():
            dt2 = pd.to_datetime(as_num[mask_num], unit="D", origin="1899-12-30", errors="coerce")
            dt.loc[mask_nat[mask_nat].index[mask_num]] = dt2

    # Formateo final
    out = pd.Series("", index=series.index, dtype="object")
    mask_ok = dt.notna()
    if mask_ok.any():
        out.loc[mask_ok] = dt.loc[mask_ok].dt.strftime("%Y-%m-%d")
    return out


def prepare_fedex_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, str, int]:
    """
    Devuelve (df_limpio, id_col, total_piezas)

    - Selecciona la mejor columna de tracking (prioridad):
        masterTrackingNumber > pieceTrackingNumber > trackingNumber
    - Normaliza Tracking Number a texto (sin científicos ni .0)
    - BULTOS desde numberOfPackages (>=1), defecto 1
    - Columnas finales y orden:
        Tracking Number | Fecha | Referencia | Ciudad | Receptor | BULTOS
    - Elimina duplicados por Tracking Number, conserva el primero
    - Calcula total de piezas (suma BULTOS)
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Tracking Number", "Fecha", "Referencia", "Ciudad", "Receptor", "BULTOS"]), "", 0

    df = df.copy()

    # 1) Columna de tracking prioritaria
    candidates = ["masterTrackingNumber", "pieceTrackingNumber", "trackingNumber"]
    id_col = next((c for c in candidates if c in df.columns), None)
    if id_col is None:
        id_col = "trackingNumber"
        df[id_col] = ""

    # 2) BULTOS
    if "numberOfPackages" in df.columns:
        b = pd.to_numeric(df["numberOfPackages"], errors="coerce").fillna(0).astype(int)
        b.loc[b <= 0] = 1
    else:
        b = pd.Series(1, index=df.index, dtype=int)
    df["BULTOS"] = b

    # 3) Campos visibles (mapas alternativos)
    fecha_col = "shipDate" if "shipDate" in df.columns else None
    ref_col   = "reference" if "reference" in df.columns else None
    city_col  = next((c for c in ["recipientCity", "recipient_city", "city"] if c in df.columns), None)
    recv_col  = next((c for c in ["recipientContactName", "recipientName", "recipient_name"] if c in df.columns), None)

    # 4) Construcción de salida con normalizaciones
    out = pd.DataFrame(index=df.index)
    out["Tracking Number"] = _stringify_tracking(df[id_col])
    out["Fecha"]           = _normalize_date(df[fecha_col]) if fecha_col else ""
    out["Referencia"]      = df[ref_col].astype(str).str.strip() if ref_col else ""
    out["Ciudad"]          = df[city_col].astype(str).str.strip() if city_col else ""
    out["Receptor"]        = df[recv_col].astype(str).str.strip() if recv_col else ""
    out["BULTOS"]          = df["BULTOS"].astype(int)

    # 5) Eliminar filas sin tracking
    out = out.loc[out["Tracking Number"].astype(str).str.strip() != ""]

    # 6) Eliminar duplicados por Tracking Number
    out = out.drop_duplicates(subset=["Tracking Number"], keep="first", ignore_index=True)

    # 7) Total piezas
    total_piezas = int(out["BULTOS"].sum()) if not out.empty else 0

    return out, id_col, total_piezas


# ========== Utilidades openpyxl para FedEx / Urbano (formato profesional) ==========

def insertar_bloque_firma_ws(ws) -> None:
    """
    Inserta bloque de firma al final con líneas dibujadas.
    Genera:
        [Nombre quien recibe:]  [__________ (merge B..D)]
        [Firma quien recibe:]   [__________ (merge B..D)]
    """
    from openpyxl.styles import Alignment, Side, Border
    from openpyxl.utils import get_column_letter

    ncols = ws.max_column or 2
    # Usamos hasta la columna D (4) para el área de la línea, o menos si la hoja es más corta.
    right = max(2, min(ncols, 4))

    ws.append([])

    # Fila "Nombre quien recibe:"
    r1 = ws.max_row + 1
    ws.cell(row=r1, column=1, value="Nombre quien recibe:")
    ws.merge_cells(start_row=r1, start_column=2, end_row=r1, end_column=right)
    for c in range(2, right + 1):
        ws.cell(row=r1, column=c, value="")

    # Fila "Firma quien recibe:"
    r2 = r1 + 1
    ws.cell(row=r2, column=1, value="Firma quien recibe:")
    ws.merge_cells(start_row=r2, start_column=2, end_row=r2, end_column=right)
    for c in range(2, right + 1):
        ws.cell(row=r2, column=c, value="")

    # Dibuja líneas (borde superior e inferior) en el rango fusionado
    from openpyxl.styles import Side, Border
    thin = Side(style="thin")
    line_border = Border(top=thin, bottom=thin)
    for r in (r1, r2):
        for c in range(2, right + 1):
            ws.cell(row=r, column=c).border = line_border

    # Alineación a la izquierda
    from openpyxl.styles import Alignment
    for r in (r1, r2):
        for c in range(1, right + 1):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="left", vertical="center")


def agregar_footer_info_ws(ws, total_piezas: int) -> None:
    """
    Agrega pie con fecha/hora e indicador de total de piezas.
    Ej.:  "Impresa el: 20250820 12:49  |  Total Piezas: 7"
    """
    from openpyxl.styles import Alignment, Font

    ts = datetime.now().strftime("%Y%m%d %H:%M")
    texto = f"Impresa el: {ts}  |  Total Piezas: {total_piezas}"

    ws.append([])
    r = ws.max_row + 1
    ws.cell(row=r, column=1, value=texto)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=max(2, ws.max_column))
    cell = ws.cell(row=r, column=1)
    cell.font = Font(size=9, italic=True)
    cell.alignment = Alignment(horizontal="left", vertical="center")


def formatear_tabla_ws(ws) -> None:
    """
    Aplica formato tipo “listado profesional”:
    - Encabezados (fila 2) en negrita y centrados, con borde inferior
    - Datos con borde fino y alineación adecuada
    - Anchos mínimos de columnas pensados para FedEx:
        Tracking Number | Fecha | Referencia | Ciudad | Receptor | BULTOS
        22, 12, 18, 18, 22, 8
    """
    from openpyxl.styles import Font, Alignment, Border, Side

    font_base = Font(name="Segoe UI", size=10)
    font_bold = Font(name="Segoe UI", size=10, bold=True)
    thin = Side(style="thin")
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    header_row = 2  # porque la fila 1 es el título
    max_col = ws.max_column
    max_row = ws.max_row

    # Encabezados
    for c in range(1, max_col + 1):
        cell = ws.cell(row=header_row, column=c)
        cell.font = font_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(bottom=thin)

    # Datos
    for r in range(header_row + 1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = font_base
            cell.border = border_all
            if c == max_col:  # BULTOS
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Anchos mínimos sugeridos
    min_widths = [22, 12, 18, 18, 22, 8]
    for i, w in enumerate(min_widths, start=1):
        if i > max_col:
            break
        col_letter = ws.cell(row=1, column=i).column_letter
        cur = ws.column_dimensions[col_letter].width
        if cur is None or cur < w:
            ws.column_dimensions[col_letter].width = w
