# app/services/informes_existencia_service.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

import pandas as pd

EXISTENCE_COLUMNS = [
    "Código",
    "Producto",
    "Fecha",
    "Documento",
    "Modalidad",
    "Unidad de stock",
    "Bodega",
    "Ubicación",
    "Cantidad",
    "N° Serie",
    "Entrada",
    "Salida",
    "Saldo",
]

_PRODUCT_HEADER_RE = re.compile(r"^\s*(?P<codigo>[^-]+?)\s*-\s*(?P<producto>.+?)\s*$")


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _clean_text(value) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\u200b", "")
    return " ".join(text.strip().split())


def _parse_number(value) -> int:
    text = _clean_text(value)
    if not text:
        return 0
    text = text.replace(".", "").replace(",", ".")
    try:
        return int(round(float(text)))
    except Exception:
        return 0


def _split_product_header(value: str) -> tuple[str, str] | None:
    text = _clean_text(value)
    if not text:
        return None
    match = _PRODUCT_HEADER_RE.match(text)
    if not match:
        return None
    return _clean_text(match.group("codigo")), _clean_text(match.group("producto"))


def _is_probable_date(value: str) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    return bool(re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", text))


def _extract_xlsx_sheet_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.iter():
                if _local_name(si.tag) != "si":
                    continue
                parts = [t.text or "" for t in si.iter() if _local_name(t.tag) == "t"]
                shared_strings.append("".join(parts))

        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels
            if _local_name(rel.tag) == "Relationship"
        }

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        first_sheet = next(node for node in workbook.iter() if _local_name(node.tag) == "sheet")
        rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = rel_map[rel_id]
        sheet_path = str(PurePosixPath(target.lstrip("/")))
        if not sheet_path.startswith("xl/"):
            sheet_path = f"xl/{sheet_path}"

        worksheet = ET.fromstring(zf.read(sheet_path))
        rows: list[list[str]] = []
        for row in worksheet.iter():
            if _local_name(row.tag) != "row":
                continue
            values_by_col: dict[int, str] = {}
            max_col = 0
            for cell in row:
                if _local_name(cell.tag) != "c":
                    continue
                ref = cell.attrib.get("r", "")
                letters = "".join(ch for ch in ref if ch.isalpha())
                if not letters:
                    continue
                col_index = 0
                for ch in letters:
                    col_index = col_index * 26 + (ord(ch.upper()) - 64)
                max_col = max(max_col, col_index)

                cell_type = cell.attrib.get("t", "")
                value = ""
                for child in cell:
                    if _local_name(child.tag) == "v":
                        value = child.text or ""
                        break
                    if _local_name(child.tag) == "is":
                        value = "".join(
                            t_node.text or ""
                            for t_node in child.iter()
                            if _local_name(t_node.tag) == "t"
                        )
                        break
                if cell_type == "s" and value != "":
                    value = shared_strings[int(value)]
                values_by_col[col_index] = _clean_text(value)
            rows.append([values_by_col.get(i, "") for i in range(1, max_col + 1)])
        return rows


def _read_sheet_rows(path: Path) -> list[list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _extract_xlsx_sheet_rows(path)
    if suffix == ".xls":
        try:
            df = pd.read_excel(path, header=None, engine="xlrd").fillna("")
        except ImportError as exc:
            raise RuntimeError(
                "Missing optional dependency 'xlrd'. Instala xlrd >= 2.0.1 para abrir archivos .xls."
            ) from exc
        return [[_clean_text(value) for value in row] for row in df.values.tolist()]
    raise ValueError("Formato no soportado. Usa archivos .xlsx o .xls")


def load_product_movements(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"No existe el archivo: {source}")

    rows = _read_sheet_rows(source)
    if len(rows) < 2:
        return pd.DataFrame(columns=EXISTENCE_COLUMNS)

    records: list[dict[str, object]] = []
    current_code = ""
    current_product = ""
    current_unit = ""

    for row in rows[1:]:
        padded = (row + [""] * 11)[:11]
        first_value = _clean_text(padded[0])
        header_candidate = _split_product_header(first_value)

        if header_candidate and not _is_probable_date(first_value) and not any(
            _clean_text(v)
            for v in (
                padded[1],
                padded[2],
                padded[4],
                padded[5],
                padded[6],
                padded[7],
                padded[8],
                padded[9],
                padded[10],
            )
        ):
            current_code, current_product = header_candidate
            current_unit = _clean_text(padded[3]) or current_unit
            continue

        has_movement_data = any(_clean_text(v) for v in padded[1:]) or _is_probable_date(first_value)
        if not current_code or not current_product or not has_movement_data:
            continue

        records.append(
            {
                "Código": current_code,
                "Producto": current_product,
                "Fecha": first_value,
                "Documento": _clean_text(padded[1]),
                "Modalidad": _clean_text(padded[2]),
                "Unidad de stock": _clean_text(padded[3]) or current_unit,
                "Bodega": _clean_text(padded[4]),
                "Ubicación": _clean_text(padded[5]),
                "Cantidad": _parse_number(padded[6]),
                "N° Serie": _clean_text(padded[7]),
                "Entrada": _parse_number(padded[8]),
                "Salida": _parse_number(padded[9]),
                "Saldo": _parse_number(padded[10]),
            }
        )

    return pd.DataFrame(records, columns=EXISTENCE_COLUMNS)
