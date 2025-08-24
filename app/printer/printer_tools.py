# app/printer/printer_tools.py
# -*- coding: utf-8 -*-
"""
Herramientas de impresión y preparación de datos para FedEx/Urbano.

• prepare_fedex_dataframe(df)   -> DataFrame normalizado y consolidado (suma BULTOS)
• prepare_urbano_dataframe(df)  -> DataFrame normalizado y total PIEZAS
• insertar_bloque_firma_ws(ws)  -> Bloque "Nombre/Firma" al final de la hoja
• agregar_footer_info_ws(ws,t)  -> Pie con timestamp y total de piezas
• formatear_tabla_ws(ws)        -> Estilo de tabla profesional (anchos/bordes auto por modo)

Notas:
- La vista previa puede llamar a prepare_fedex_dataframe / prepare_urbano_dataframe
  para que el usuario vea exactamente lo que se imprimirá.
- Todas las funciones openpyxl modifican el workbook in-place.
"""

from __future__ import annotations

from datetime import datetime
from typing import Tuple
import pandas as pd


# ======================================================================
#                      Normalización / Limpieza de datos
# ======================================================================

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
    Devuelve (df_limpio, id_col, total_piezas)

    - Prioridad de ID: masterTrackingNumber > pieceTrackingNumber > trackingNumber
    - Normaliza tracking (texto limpio) y fechas
    - BULTOS: usa numberOfPackages (>=1) o 1 por defecto
    - Agrupa por tracking y **suma** BULTOS (no se pierden piezas)
    - Columnas finales y orden:
        Tracking Number | Fecha | Referencia | Ciudad | Receptor | BULTOS
    - Filtro extra: solo conserva filas con Tracking y Receptor no vacíos.
    """
    cols_final = ["Tracking Number", "Fecha", "Referencia", "Ciudad", "Receptor", "BULTOS"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols_final), "", 0

    df = df.copy()

    # 1) Selección de columna de tracking (por prioridad)
    candidates = ["masterTrackingNumber", "pieceTrackingNumber", "trackingNumber"]
    id_col = next((c for c in candidates if c in df.columns), None)
    if id_col is None:
        return pd.DataFrame(columns=cols_final), "", 0

    # 2) BULTOS (mínimo 1)
    if "numberOfPackages" in df.columns:
        b = pd.to_numeric(df["numberOfPackages"], errors="coerce").fillna(0).astype(int)
        b.loc[b <= 0] = 1
    else:
        b = pd.Series(1, index=df.index, dtype=int)
    df["BULTOS"] = b

    # 3) Mapeo de columnas visibles (acepta alias comunes)
    fecha_col = "shipDate" if "shipDate" in df.columns else None
    ref_col   = "reference" if "reference" in df.columns else None
    city_col  = next((c for c in ["recipientCity", "recipient_city", "city"] if c in df.columns), None)
    recv_col  = next((c for c in ["recipientContactName", "recipientName", "recipient_name"] if c in df.columns), None)

    # 4) Construcción base + normalización
    base = pd.DataFrame(index=df.index)
    base["Tracking Number"] = _stringify_tracking(df[id_col])
    base["Fecha"]           = _normalize_date(df[fecha_col]) if fecha_col else pd.Series("", index=df.index, dtype="string")
    base["Referencia"]      = _stringify_generic(df[ref_col]) if ref_col else pd.Series("", index=df.index, dtype="string")
    base["Ciudad"]          = df[city_col].astype("string").str.strip() if city_col else pd.Series("", index=df.index, dtype="string")
    base["Receptor"]        = df[recv_col].astype("string").str.strip() if recv_col else pd.Series("", index=df.index, dtype="string")
    base["BULTOS"]          = df["BULTOS"].astype(int)

    # 5) Filtro: Tracking y Receptor obligatorios
    base = base.loc[
        (base["Tracking Number"] != "") &
        (base["Receptor"] != "")
    ].copy()
    if base.empty:
        return pd.DataFrame(columns=cols_final), id_col, 0

    # 6) Agrupar por tracking y **sumar** BULTOS
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

    # 7) Orden sugerido: Fecha ascendente, luego Tracking
    if "Fecha" in grouped.columns:
        _sd = pd.to_datetime(grouped["Fecha"], errors="coerce")
        grouped = grouped.assign(_sd=_sd).sort_values(["_sd", "Tracking Number"], na_position="last").drop(columns=["_sd"])
    else:
        grouped = grouped.sort_values(["Tracking Number"])

    total_piezas = int(grouped["BULTOS"].sum())
    return grouped.reset_index(drop=True), id_col, total_piezas


# ------------------------- URBANO -------------------------

def prepare_urbano_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Normaliza DataFrame de Urbano y devuelve (df_out, total_piezas).

    Expectativa de columnas visibles:
        GUIA | CLIENTE | LOCALIDAD | PIEZAS | COD RASTREO

    - Convierte PIEZAS a entero >= 1
    - Elimina filas completamente vacías (o sin ninguna info relevante)
    - Calcula total de PIEZAS
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

    out = pd.DataFrame(index=df.index)
    out["GUIA"]        = df[guia_col].astype("string").str.strip() if guia_col else ""
    out["CLIENTE"]     = df[cli_col].astype("string").str.strip() if cli_col else ""
    out["LOCALIDAD"]   = df[loc_col].astype("string").str.strip() if loc_col else ""
    if piezas_c:
        p = pd.to_numeric(df[piezas_c], errors="coerce").fillna(0).astype(int)
        p.loc[p <= 0] = 1
    else:
        p = pd.Series(1, index=df.index, dtype=int)
    out["PIEZAS"]      = p
    out["COD RASTREO"] = df[rastreo_c].astype("string").str.strip() if rastreo_c else ""

    # Filtra filas "basura": que no tengan ninguna columna de texto con valor
    mask_valid = out[["GUIA", "CLIENTE", "LOCALIDAD", "COD RASTREO"]].astype(str).apply(lambda s: s.str.strip() != "").any(axis=1)
    out = out.loc[mask_valid].reset_index(drop=True)

    total_piezas = int(out["PIEZAS"].sum()) if not out.empty else 0
    return out[cols_final], total_piezas


# ======================================================================
#                    Utilidades de formato (openpyxl)
# ======================================================================

def insertar_bloque_firma_ws(ws) -> None:
    """
    Inserta bloque de firma al final con líneas dibujadas.
    Genera:
        [Nombre quien recibe:]  [__________ (merge B..D)]
        [Firma quien recibe:]   [__________ (merge B..D)]
    """
    from openpyxl.styles import Alignment, Side, Border

    ncols = ws.max_column or 2
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

    thin = Side(style="thin")
    line_border = Border(top=thin, bottom=thin)
    for r in (r1, r2):
        for c in range(2, right + 1):
            ws.cell(row=r, column=c).border = line_border

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
    # Detectar si la última columna es cuantitativa (BULTOS/PIEZAS) para centrar
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
        # Fallback genérico (12px aprox. por columna)
        min_widths = [16] * max_col

    for i, w in enumerate(min_widths, start=1):
        if i > max_col:
            break
        col_letter = get_column_letter(i)
        cur = ws.column_dimensions[col_letter].width
        if cur is None or cur < w:
            ws.column_dimensions[col_letter].width = w
