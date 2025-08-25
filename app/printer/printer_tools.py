# app/printer/printer_tools.py
# -*- coding: utf-8 -*-
"""
Herramientas de impresión y preparación de datos para FedEx/Urbano.

• prepare_fedex_dataframe(df)   -> DataFrame normalizado y consolidado (suma BULTOS)
• prepare_urbano_dataframe(df)  -> DataFrame normalizado y total PIEZAS
• insertar_bloque_firma_ws(ws)  -> Bloque "Nombre/Firma" al final de la hoja
• agregar_footer_info_ws(ws,t)  -> Pie con timestamp y total de piezas
• formatear_tabla_ws(ws)        -> Estilo de tabla profesional (anchos/bordes auto por modo)
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Tuple
import numpy as np
import pandas as pd


# ======================================================================
#                      Normalización / Limpieza de datos
# ======================================================================

def _df_safe_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reemplaza pd.NA/NaN por "" y normaliza dtypes a 'object' en columnas de texto,
    para que openpyxl no falle con 'Cannot convert <NA> to Excel'.
    """
    df2 = df.copy()
    df2 = df2.replace({pd.NA: "", np.nan: ""})
    df2 = df2.replace({"nan": "", "<NA>": ""})
    for c in df2.columns:
        if pd.api.types.is_string_dtype(df2[c]) or pd.api.types.is_object_dtype(df2[c]):
            df2[c] = df2[c].astype(object)
    return df2


def _clean_text_series(series: pd.Series) -> pd.Series:
    """
    Convierte a texto, quita espacios, y normaliza valores "vacíos":
    NaN, <NA>, nan, none, null -> "" (case-insensitive).
    """
    if series is None:
        return pd.Series([], dtype="string")
    s = series.astype("string").fillna("").str.strip()
    # Marcar como vacío valores típicos de 'no dato'
    s = s.replace(
        to_replace=r"^(nan|<na>|none|null)$",
        value="",
        regex=True,
        flags=re.I if hasattr(pd, "re") else 0,  # compat: pandas antiguas ignoran flags
    )
    return s


def _stringify_tracking(series: pd.Series) -> pd.Series:
    """
    Convierte tracking a texto, sin notación científica ni '.0',
    y normaliza vacíos a "" (eliminando "nan" / "<NA>").
    """
    if series is None:
        return pd.Series([], dtype="string")

    as_num = pd.to_numeric(series, errors="coerce")
    out = pd.Series("", index=series.index, dtype="string")

    mask_num = as_num.notna()
    if mask_num.any():
        out.loc[mask_num] = as_num.loc[mask_num].astype("Int64").astype("string")

    mask_rest = ~mask_num
    if mask_rest.any():
        out.loc[mask_rest] = series.loc[mask_rest].astype("string")

    out = out.fillna("").str.strip()
    out = out.replace({"nan": "", "<NA>": ""})
    return out


def _stringify_generic(series: pd.Series) -> pd.Series:
    """
    Convierte un campo genérico a string limpio, intentando primero
    representación numérica sin '.0'. Útil para 'reference' u otros campos.
    """
    if series is None:
        return pd.Series([], dtype="string")

    as_num = pd.to_numeric(series, errors="coerce")
    out = pd.Series("", index=series.index, dtype="string")

    mask_num = as_num.notna()
    if mask_num.any():
        out.loc[mask_num] = as_num.loc[mask_num].astype("Int64").astype("string")

    mask_rest = ~mask_num
    if mask_rest.any():
        out.loc[mask_rest] = series.loc[mask_rest].astype("string")

    out = out.fillna("").str.strip()
    out = out.replace({"nan": "", "<NA>": ""})
    return out


def _normalize_date(series: pd.Series) -> pd.Series:
    """
    Normaliza fechas a 'YYYY-MM-DD'.
    Acepta string/datetime y serial Excel (días desde 1899-12-30).
    """
    if series is None:
        return pd.Series([], dtype="string")

    dt = pd.to_datetime(series, errors="coerce", utc=False)

    # Reintento para serial Excel donde falló el parseo
    mask_nat = dt.isna()
    if mask_nat.any():
        as_num = pd.to_numeric(series[mask_nat], errors="coerce")
        mask_num = as_num.notna()
        if mask_num.any():
            idx = as_num[mask_num].index
            dt2 = pd.to_datetime(as_num[mask_num], unit="D", origin="1899-12-30", errors="coerce")
            dt.loc[idx] = dt2

    out = pd.Series("", index=series.index, dtype="string")
    mask_ok = dt.notna()
    if mask_ok.any():
        out.loc[mask_ok] = dt.loc[mask_ok].dt.strftime("%Y-%m-%d")
    return out


# ------------------------- FEDEX -------------------------

def prepare_fedex_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, str, int]:
    """
    Devuelve (df_limpio, id_col, total_piezas).

    Soporta columnas en inglés y en español. Si el DF ya trae las columnas finales
    (Tracking Number | Fecha | Referencia | Ciudad | Receptor | BULTOS), se usan tal cual.
    """
    cols_final = ["Tracking Number", "Fecha", "Referencia", "Ciudad", "Receptor", "BULTOS"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols_final), "", 0

    df = df.copy()

    # 0) Si ya viene listo (p. ej., desde tu vista previa), usarlo tal cual
    if set(cols_final).issubset(df.columns):
        out = df.loc[:, cols_final].copy()
        # Normalización mínima
        out["Tracking Number"] = _stringify_tracking(out["Tracking Number"])
        out["Fecha"]           = _normalize_date(out["Fecha"])
        out["Referencia"]      = _stringify_generic(out["Referencia"])
        out["Ciudad"]          = out["Ciudad"].astype("string").str.strip()
        out["Receptor"]        = out["Receptor"].astype("string").str.strip()
        # BULTOS entero >= 1
        b = pd.to_numeric(out["BULTOS"], errors="coerce").fillna(0).astype(int)
        b.loc[b <= 0] = 1
        out["BULTOS"] = b

        # Agrupar por tracking (por si hay duplicados) y sumar piezas
        grouped = (out.groupby("Tracking Number", as_index=False)
                      .agg({
                          "Fecha": "first",
                          "Referencia": "first",
                          "Ciudad": "first",
                          "Receptor": "first",
                          "BULTOS": "sum",
                      }))
        total_piezas = int(grouped["BULTOS"].sum())
        grouped = _df_safe_for_excel(grouped)
        return grouped.reset_index(drop=True), "Tracking Number", total_piezas

    # 1) Tracking: prioridad + alias
    candidates = [
        "masterTrackingNumber", "pieceTrackingNumber", "trackingNumber",
        "Tracking Number", "tracking number", "TRACKING", "tracking",
    ]
    id_col = next((c for c in candidates if c in df.columns), None)
    if id_col is None:
        return pd.DataFrame(columns=cols_final), "", 0

    # 2) BULTOS / piezas: varios alias
    bultos_candidates = [
        "BULTOS", "bultos", "PIEZAS", "piezas", "pieces",
        "numberOfPackages", "packages", "pieceCount",
    ]
    b_col = next((c for c in bultos_candidates if c in df.columns), None)
    if b_col:
        b = pd.to_numeric(df[b_col], errors="coerce").fillna(0).astype(int)
        b.loc[b <= 0] = 1
    else:
        b = pd.Series(1, index=df.index, dtype=int)

    # 3) Alias para el resto (ES/EN)
    def pick(*names):
        return next((c for c in names if c in df.columns), None)

    fecha_col = pick("shipDate", "Ship Date", "Fecha", "fecha", "date", "Date")
    ref_col   = pick("reference", "Reference", "Referencia", "referencia", "Ref", "ref")
    city_col  = pick("recipientCity", "recipient_city", "city", "City", "Ciudad", "ciudad", "Localidad", "localidad")
    recv_col  = pick("recipientContactName", "recipientName", "recipient_name",
                     "Receptor", "receptor", "Destinatario", "destinatario")

    # 4) Construcción + normalización
    base = pd.DataFrame(index=df.index)
    base["Tracking Number"] = _stringify_tracking(df[id_col])
    base["Fecha"]           = _normalize_date(df[fecha_col]) if fecha_col else pd.Series("", index=df.index, dtype="string")
    base["Referencia"]      = _stringify_generic(df[ref_col]) if ref_col else pd.Series("", index=df.index, dtype="string")
    base["Ciudad"]          = df[city_col].astype("string").str.strip() if city_col else pd.Series("", index=df.index, dtype="string")
    base["Receptor"]        = df[recv_col].astype("string").str.strip() if recv_col else pd.Series("", index=df.index, dtype="string")
    base["BULTOS"]          = b

    # 5) Filtro: siempre exigir Tracking; Receptor sólo si existe
    mask = base["Tracking Number"] != ""
    if recv_col:
        mask &= base["Receptor"] != ""
    base = base.loc[mask].copy()
    if base.empty:
        return pd.DataFrame(columns=cols_final), id_col, 0

    # 6) Agrupar + sumar BULTOS (primer no vacío para texto)
    def _first_non_empty(s: pd.Series) -> str:
        s2 = s.fillna("").astype("string")
        non_empty = s2[s2.str.strip() != ""]
        return non_empty.iloc[0] if not non_empty.empty else (s2.iloc[0] if len(s2) else "")

    grouped = (
        base.groupby("Tracking Number", as_index=False)
            .agg({
                "Fecha": _first_non_empty,
                "Referencia": _first_non_empty,
                "Ciudad": _first_non_empty,
                "Receptor": _first_non_empty,
                "BULTOS": "sum",
            })
    )

    # 7) Ordenar por fecha si existe
    if "Fecha" in grouped.columns:
        _sd = pd.to_datetime(grouped["Fecha"], errors="coerce")
        grouped = grouped.assign(_sd=_sd).sort_values(["_sd", "Tracking Number"], na_position="last").drop(columns=["_sd"])
    else:
        grouped = grouped.sort_values(["Tracking Number"])

    total_piezas = int(grouped["BULTOS"].sum())
    grouped = _df_safe_for_excel(grouped)
    return grouped.reset_index(drop=True), id_col, total_piezas


# ------------------------- URBANO -------------------------

def prepare_urbano_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Normaliza DataFrame de Urbano y devuelve (df_out, total_piezas).

    Expectativa de columnas visibles:
        GUIA | CLIENTE | LOCALIDAD | PIEZAS | COD RASTREO

    Reglas especiales:
    - Trata 'nan', '<NA>', 'none', 'null' como vacío (no pasan filtro).
    - Excluye filas de 'total' (texto que contenga 'total' o todas las
      columnas de texto vacías). El total se mostrará sólo en el footer.
    """
    cols_final = ["GUIA", "CLIENTE", "LOCALIDAD", "PIEZAS", "COD RASTREO"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols_final), 0

    df = df.copy()

    # Helper para elegir alias más probable
    def pick(*names):
        for n in names:
            if n in df.columns:
                return n
        return None

    guia_col  = pick("GUIA", "guia", "Guia")
    cli_col   = pick("CLIENTE", "cliente", "Cliente")
    loc_col   = pick("LOCALIDAD", "localidad", "Localidad", "CIUDAD", "ciudad")
    piezas_c  = pick("PIEZAS", "piezas", "Piezas", "BULTOS", "bultos")
    rastreo_c = pick("COD RASTREO", "COD_RASTREO", "codRastreo", "TRACKING", "tracking")

    # Construcción base + limpieza de texto (marcando 'nan' y similares como vacío)
    out = pd.DataFrame(index=df.index)

    txt_guia  = _clean_text_series(df[guia_col])  if guia_col  else pd.Series("", index=df.index, dtype="string")
    txt_cli   = _clean_text_series(df[cli_col])   if cli_col   else pd.Series("", index=df.index, dtype="string")
    txt_loc   = _clean_text_series(df[loc_col])   if loc_col   else pd.Series("", index=df.index, dtype="string")
    txt_track = _clean_text_series(df[rastreo_c]) if rastreo_c else pd.Series("", index=df.index, dtype="string")

    out["GUIA"]        = txt_guia
    out["CLIENTE"]     = txt_cli
    out["LOCALIDAD"]   = txt_loc
    out["COD RASTREO"] = txt_track

    # PIEZAS
    if piezas_c:
        p = pd.to_numeric(df[piezas_c], errors="coerce").fillna(0).astype(int)
        p.loc[p <= 0] = 1
    else:
        p = pd.Series(1, index=df.index, dtype=int)
    out["PIEZAS"]      = p

    # --- Filtro de filas válidas ---
    # 1) Filas con alguna columna de texto no vacía
    has_any_text = out[["GUIA", "CLIENTE", "LOCALIDAD", "COD RASTREO"]].apply(lambda s: s.str.strip() != "", axis=0).any(axis=1)

    # 2) Excluir filas "totales": si en cualquiera de las columnas de texto aparece 'total'
    contains_total = out[["GUIA", "CLIENTE", "LOCALIDAD", "COD RASTREO"]].apply(
        lambda s: s.str.contains(r"\btotal\b", case=False, regex=True, na=False), axis=0
    ).any(axis=1)

    # 3) Fila completamente sin texto (todas vacías) -> no se muestra en la grilla impresa
    all_text_empty = out[["GUIA", "CLIENTE", "LOCALIDAD", "COD RASTREO"]].apply(lambda s: s.str.strip() == "", axis=0).all(axis=1)

    mask_valid = has_any_text & (~contains_total) & (~all_text_empty)
    out = out.loc[mask_valid].reset_index(drop=True)

    total_piezas = int(out["PIEZAS"].sum()) if not out.empty else 0
    out = out[cols_final]
    out = _df_safe_for_excel(out)
    return out, total_piezas


# ======================================================================
#                    Utilidades de formato (openpyxl)
# ======================================================================

def insertar_bloque_firma_ws(ws) -> None:
    """
    Inserta bloque de firma al final con líneas dibujadas.
    Genera:
        [Nombre quien recibe:]  [__________ (merge B..D)]
        [Firma quien recibe:]   [__________ (merge B..D)]

    Importante:
    - En openpyxl sólo se escribe valor en la **celda superior izquierda**
      de un rango fusionado. No asignes en las demás celdas del merge.
    """
    from openpyxl.styles import Alignment, Side, Border

    ncols = ws.max_column or 2
    right = max(2, min(ncols, 4))  # fusionaremos desde la col 2 hasta 'right'

    # Separador visual
    ws.append([])

    # Fila "Nombre quien recibe:"
    r1 = ws.max_row + 1
    ws.cell(row=r1, column=1, value="Nombre quien recibe:")
    ws.merge_cells(start_row=r1, start_column=2, end_row=r1, end_column=right)
    ws.cell(row=r1, column=2, value="")

    # Fila "Firma quien recibe:"
    r2 = r1 + 1
    ws.cell(row=r2, column=1, value="Firma quien recibe:")
    ws.merge_cells(start_row=r2, start_column=2, end_row=r2, end_column=right)
    ws.cell(row=r2, column=2, value="")

    # Dibujar líneas (bordes superior/inferior) sobre el rango fusionado
    thin = Side(style="thin")
    line_border = Border(top=thin, bottom=thin)
    for r in (r1, r2):
        for c in range(2, right + 1):
            ws.cell(row=r, column=c).border = line_border

    # Alineación
    for r in (r1, r2):
        for c in range(1, right + 1):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="left", vertical="center")


def agregar_footer_info_ws(ws, total_piezas: int) -> None:
    """
    Agrega pie con fecha/hora e indicador de total de piezas.
    Ej.:  "Impresa el: 2025-08-20 12:49  |  Total Piezas: 7"
    """
    from openpyxl.styles import Alignment, Font

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    texto = f"Impresa el: {ts}  |  Total Piezas: {total_piezas}"

    ws.append([])
    r = ws.max_row + 1
    ws.cell(row=r, column=1, value=texto)

    end_col = max(2, ws.max_column)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=end_col)

    cell = ws.cell(row=r, column=1)
    cell.font = Font(size=9, italic=True)
    cell.alignment = Alignment(horizontal="left", vertical="center")


def formatear_tabla_ws(ws) -> None:
    """
    Aplica formato tipo “listado profesional”:
    - Encabezados (fila 2) en negrita y centrados, con borde inferior
    - Datos con borde fino y alineación adecuada
    - Anchos mínimos de columnas auto por modo:
        • FEDEX:   Tracking Number | Fecha | Referencia | Ciudad | Receptor | BULTOS
                    22, 12, 18, 18, 22, 8
        • URBANO:  GUIA | CLIENTE | LOCALIDAD | PIEZAS | COD RASTREO
                    18, 22, 18, 8, 22
    """
    from openpyxl.styles import Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    font_base = Font(name="Segoe UI", size=10)
    font_bold = Font(name="Segoe UI", size=10, bold=True)
    thin = Side(style="thin")
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    header_row = 2  # la fila 1 es el título generado por generar_excel_temporal
    max_col = ws.max_column
    max_row = ws.max_row

    # Leer nombres de encabezados desde la fila 2 para ajustar por modo
    headers = []
    for c in range(1, max_col + 1):
        headers.append(str(ws.cell(row=header_row, column=c).value or "").strip())

    # Detectar modo por headers
    is_fedex = headers[:6] == ["Tracking Number", "Fecha", "Referencia", "Ciudad", "Receptor", "BULTOS"]
    is_urbano = headers[:5] == ["GUIA", "CLIENTE", "LOCALIDAD", "PIEZAS", "COD RASTREO"]

    # Encabezados
    for c in range(1, max_col + 1):
        cell = ws.cell(row=header_row, column=c)
        cell.font = font_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(bottom=thin)

    # Datos
    last_is_qty = False
    if headers:
        last_is_qty = headers[-1].upper() in {"BULTOS", "PIEZAS"}

    for r in range(header_row + 1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = font_base
            cell.border = border_all
            if last_is_qty and c == max_col:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Anchos mínimos sugeridos por modo
    if is_fedex:
        min_widths = [22, 12, 18, 18, 22, 8]
    elif is_urbano:
        min_widths = [18, 22, 18, 8, 22]
    else:
        min_widths = [16] * max_col

    for i, w in enumerate(min_widths, start=1):
        if i > max_col:
            break
        col_letter = get_column_letter(i)
        cur = ws.column_dimensions[col_letter].width
        if cur is None or cur < w:
            ws.column_dimensions[col_letter].width = w
