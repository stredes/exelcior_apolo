# Módulo: printer_inventario_codigo.py
# Descripción: Impresión automática del inventario filtrado por código.

from __future__ import annotations

import os
import platform
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.core.impression_tools import enviar_a_impresora_configurable
from app.core.logger_eventos import log_evento


PRINT_COLUMN_MAP = {
    "Código": "Código",
    "Producto": "Producto",
    "Bodega": "Bodega",
    "Ubicación": "Ubicación",
    "N° Serie": "N° Serie",
    "Lote": "Lote",
    "Fecha Vencimiento": "Fecha Vencimiento",
    "Saldo Stock": "Saldo Stock",
}

PRINT_COLUMN_ORDER = list(PRINT_COLUMN_MAP.values())


def _prepare_inventory_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    normalized = df.rename(columns=PRINT_COLUMN_MAP).copy()
    missing = [column for column in PRINT_COLUMN_ORDER if column not in normalized.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas para imprimir inventario: {missing}")

    prepared = normalized.loc[:, PRINT_COLUMN_ORDER].copy()
    prepared["Saldo Stock"] = pd.to_numeric(prepared["Saldo Stock"], errors="coerce").fillna(0).astype(int)
    prepared["Fecha Vencimiento"] = prepared["Fecha Vencimiento"].fillna("").astype(str)

    for column in PRINT_COLUMN_ORDER:
        if column != "Saldo Stock":
            prepared[column] = prepared[column].fillna("").astype(str).str.strip()

    total_cantidad = int(prepared["Saldo Stock"].sum())
    return prepared, total_cantidad


def _prepare_duplicate_groups(df: pd.DataFrame) -> tuple[list[tuple[str, str, pd.DataFrame]], int]:
    prepared, total_cantidad = _prepare_inventory_dataframe(df)
    groups: list[tuple[str, str, pd.DataFrame]] = []
    for (codigo, producto), group in prepared.groupby(["Código", "Producto"], sort=False):
        groups.append((str(codigo), str(producto), group.reset_index(drop=True)))
    return groups, total_cantidad


def _format_inventory_sheet(sheet, df: pd.DataFrame, total_cantidad: int, titulo: str) -> None:
    total_columnas = len(df.columns)
    data_start_row = 3
    data_end_row = data_start_row + len(df) - 1
    total_row = data_end_row + 1

    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columnas)

    title_cell = sheet.cell(row=1, column=1)
    title_cell.value = titulo
    title_cell.font = Font(name="Segoe UI", bold=True, size=12)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    header_font = Font(name="Segoe UI", bold=True, size=10)
    body_font = Font(name="Segoe UI", size=10)
    highlight_font = Font(name="Segoe UI", bold=True, size=10)
    borde_fino = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    total_fill = PatternFill(fill_type="solid", fgColor="E2E8F0")
    header_fill = PatternFill(fill_type="solid", fgColor="D9E2F3")

    width_map = {
        "Código": 16,
        "Producto": 38,
        "Bodega": 14,
        "Ubicación": 18,
        "N° Serie": 18,
        "Lote": 14,
        "Fecha Vencimiento": 18,
        "Saldo Stock": 12,
    }

    for col_idx, header in enumerate(df.columns, start=1):
        col_letter = get_column_letter(col_idx)
        sheet.column_dimensions[col_letter].width = width_map.get(header, 18)

        header_cell = sheet.cell(row=2, column=col_idx)
        header_cell.font = header_font
        header_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        header_cell.border = borde_fino
        header_cell.fill = header_fill

    for row in sheet.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=total_columnas):
        for cell in row:
            cell.font = body_font
            cell.border = borde_fino
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    label_cell = sheet.cell(row=total_row, column=max(1, total_columnas - 1), value="Total")
    label_cell.font = highlight_font
    label_cell.alignment = Alignment(horizontal="right", vertical="center")
    label_cell.border = borde_fino
    label_cell.fill = total_fill

    total_cell = sheet.cell(row=total_row, column=total_columnas, value=total_cantidad)
    total_cell.font = highlight_font
    total_cell.alignment = Alignment(horizontal="center", vertical="center")
    total_cell.border = borde_fino
    total_cell.fill = total_fill

    sheet.freeze_panes = "A3"
    sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_margins.left = 0.2
    sheet.page_margins.right = 0.2
    sheet.page_margins.top = 0.3
    sheet.page_margins.bottom = 0.3
    sheet.page_margins.header = 0.1
    sheet.page_margins.footer = 0.1
    sheet.print_options.horizontalCentered = True


def _format_duplicate_inventory_sheet(sheet, groups: list[tuple[str, str, pd.DataFrame]], total_cantidad: int, titulo: str) -> None:
    total_columnas = len(PRINT_COLUMN_ORDER)
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_columnas)

    title_cell = sheet.cell(row=1, column=1)
    title_cell.value = titulo
    title_cell.font = Font(name="Segoe UI", bold=True, size=12)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    header_font = Font(name="Segoe UI", bold=True, size=10)
    body_font = Font(name="Segoe UI", size=10)
    group_font = Font(name="Segoe UI", bold=True, size=10)
    highlight_font = Font(name="Segoe UI", bold=True, size=10)
    borde_fino = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    total_fill = PatternFill(fill_type="solid", fgColor="E2E8F0")
    header_fill = PatternFill(fill_type="solid", fgColor="D9E2F3")
    group_fill = PatternFill(fill_type="solid", fgColor="DCE7F8")

    width_map = {
        "Código": 16,
        "Producto": 38,
        "Bodega": 16,
        "Ubicación": 18,
        "N° Serie": 18,
        "Lote": 14,
        "Fecha Vencimiento": 18,
        "Saldo Stock": 12,
    }

    for col_idx, header in enumerate(PRINT_COLUMN_ORDER, start=1):
        col_letter = get_column_letter(col_idx)
        sheet.column_dimensions[col_letter].width = width_map.get(header, 18)

        header_cell = sheet.cell(row=2, column=col_idx, value=header)
        header_cell.font = header_font
        header_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        header_cell.border = borde_fino
        header_cell.fill = header_fill

    current_row = 3
    for codigo, producto, group in groups:
        total_stock = int(pd.to_numeric(group["Saldo Stock"], errors="coerce").fillna(0).sum())
        ubic_count = group["Ubicación"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()

        group_values = [
            codigo,
            producto,
            "",
            f"Producto con {ubic_count} ubicaciones",
            "",
            "",
            "",
            total_stock,
        ]
        for col_idx, value in enumerate(group_values, start=1):
            cell = sheet.cell(row=current_row, column=col_idx, value=value)
            cell.font = group_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = borde_fino
            cell.fill = group_fill
        current_row += 1

        for _, row in group.iterrows():
            for col_idx, header in enumerate(PRINT_COLUMN_ORDER, start=1):
                cell = sheet.cell(row=current_row, column=col_idx, value=row[header])
                cell.font = body_font
                cell.border = borde_fino
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            current_row += 1

    label_cell = sheet.cell(row=current_row, column=max(1, total_columnas - 1), value="Total")
    label_cell.font = highlight_font
    label_cell.alignment = Alignment(horizontal="right", vertical="center")
    label_cell.border = borde_fino
    label_cell.fill = total_fill

    total_cell = sheet.cell(row=current_row, column=total_columnas, value=total_cantidad)
    total_cell.font = highlight_font
    total_cell.alignment = Alignment(horizontal="center", vertical="center")
    total_cell.border = borde_fino
    total_cell.fill = total_fill

    sheet.freeze_panes = "A3"
    sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_margins.left = 0.2
    sheet.page_margins.right = 0.2
    sheet.page_margins.top = 0.3
    sheet.page_margins.bottom = 0.3
    sheet.page_margins.header = 0.1
    sheet.page_margins.footer = 0.1
    sheet.print_options.horizontalCentered = True


def _cleanup_temp_file_later(file_path: Path, delay_seconds: int = 180):
    def _cleanup():
        time.sleep(delay_seconds)
        try:
            file_path.unlink(missing_ok=True)
        except Exception as cleanup_error:
            log_evento(
                f"No se pudo eliminar temporal de inventario por codigo: {cleanup_error}",
                "warning",
            )

    threading.Thread(target=_cleanup, daemon=True).start()


def print_inventario_codigo(file_path=None, config=None, df: pd.DataFrame = None):
    """
    Entrada estandarizada desde printer_map. Imprime un Excel con formato a partir de un DataFrame.
    Compatible con llamada antigua: print_inventario_codigo(df=...).
    """
    temp_path: Path | None = None
    try:
        if isinstance(file_path, pd.DataFrame) and df is None:
            df = file_path
        if df is None:
            raise ValueError("No se recibio DataFrame para impresion de inventario por codigo.")
        if df.empty:
            raise ValueError("El DataFrame del inventario por codigo esta vacio.")

        fecha = datetime.now().strftime("%d/%m/%Y")
        cfg = config if isinstance(config, dict) else {}
        print_mode = str(cfg.get("inventory_print_mode", "")).strip().lower()
        is_duplicate_mode = print_mode == "duplicados"

        titulo = f"INVENTARIO POR DUPLICADOS - {fecha}" if is_duplicate_mode else f"INVENTARIO POR CODIGO - {fecha}"
        df_to_export, total_cantidad = _prepare_inventory_dataframe(df)

        with NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            temp_path = Path(temp_file.name)

        if is_duplicate_mode:
            groups, total_cantidad = _prepare_duplicate_groups(df)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Inventario"
            _format_duplicate_inventory_sheet(sheet, groups, total_cantidad, titulo)
            workbook.save(temp_path)
        else:
            with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
                df_to_export.to_excel(writer, index=False, sheet_name="Inventario", startrow=1)
                sheet = writer.book["Inventario"]
                _format_inventory_sheet(sheet, df_to_export, total_cantidad, titulo)

        log_evento(f"Archivo temporal generado para impresion por codigo: {temp_path}", "info")
        _enviar_a_impresora(temp_path, config=config)
        log_evento("Impresion de inventario por codigo completada correctamente.", "info")

    except Exception as e:
        log_evento(f"Error en impresion por codigo: {e}", "error")
        raise RuntimeError(f"Error al imprimir inventario por codigo: {e}")
    finally:
        if temp_path is not None:
            _cleanup_temp_file_later(temp_path)


def _enviar_a_impresora(file_path: Path, config=None):
    sistema = platform.system()
    try:
        if sistema == "Windows":
            enviar_a_impresora_configurable(file_path, config=config, default_timeout_s=120)
        elif sistema == "Linux":
            enviar_a_impresora_configurable(file_path, config=config, default_timeout_s=120)
        elif sistema == "Darwin":
            enviar_a_impresora_configurable(file_path, config=config, default_timeout_s=120)
        else:
            raise OSError("Sistema operativo no compatible para impresion automatica.")
    except Exception as e:
        log_evento(f"Error al imprimir archivo Excel: {e}", "error")
        raise RuntimeError(f"Error al enviar a impresora: {e}")
