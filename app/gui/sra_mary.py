# Module: sra_mary.py
# Description: Gestion de clientes y dias de despacho preferidos para FedEx y Urbano.

from __future__ import annotations

import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd


DB_PATH = Path("data/sra_mary_db.json")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if not DB_PATH.exists():
    DB_PATH.write_text("[]", encoding="utf-8")

logger = logging.getLogger("eventos_logger")


def guardar_datos_json(data: list) -> None:
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("Base de datos Sra Mary actualizada.")
    except Exception as e:
        logger.error(f"No se pudo guardar Sra Mary DB: {e}")
        raise


def cargar_clientes() -> list:
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"No se pudo cargar Sra Mary DB: {e}")
        return []


def _norm_text(s: str) -> str:
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split())


def _decode_day_codes(value: str) -> list[str]:
    raw = _norm_text(value).upper()
    if not raw:
        return []
    if "SOLO VIAJE ESPECIAL" in raw:
        return []
    mapping = {
        "L": "Lunes",
        "M": "Martes",
        "X": "Miércoles",
        "J": "Jueves",
        "V": "Viernes",
        "S": "Sábado",
        "D": "Domingo",
    }
    dias = []
    for ch in raw:
        d = mapping.get(ch)
        if d and d not in dias:
            dias.append(d)
    return dias


def _read_transito_ods(path: Path) -> dict[tuple[str, str], set[str]]:
    ns = {
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    }

    def cell_text(cell) -> str:
        vals = []
        for p in cell.findall(".//text:p", ns):
            t = "".join(p.itertext()).strip()
            if t:
                vals.append(t)
        return " ".join(vals)

    with zipfile.ZipFile(path, "r") as zf:
        root = ET.fromstring(zf.read("content.xml"))

    rows = None
    for t in root.findall(".//table:table", ns):
        name = t.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name", "")
        if _norm_text(name) not in ("ubigeo", ""):
            continue
        tmp_rows = []
        for tr in t.findall("table:table-row", ns):
            rep_rows = int(tr.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-rows-repeated", "1"))
            one_row = []
            for tc in tr.findall("table:table-cell", ns):
                rep_cols = int(tc.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated", "1"))
                txt = cell_text(tc)
                one_row.extend([txt] * rep_cols)
            while one_row and one_row[-1] == "":
                one_row.pop()
            for _ in range(rep_rows):
                tmp_rows.append(list(one_row))
        if any(any(str(c).strip() for c in r) for r in tmp_rows):
            rows = tmp_rows
            break

    if not rows or len(rows) < 3:
        return {}

    max_cols = max((len(r) for r in rows), default=0)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]
    headers = [str(v).strip() for v in rows[1]]
    df = pd.DataFrame(rows[2:], columns=headers)

    cols_norm = {_norm_text(c): c for c in df.columns}
    region_col = cols_norm.get("region")
    comuna_col = cols_norm.get("comuna")
    dias_col = cols_norm.get("dias de salida de agencia")
    if not region_col or not comuna_col or not dias_col:
        return {}

    out: dict[tuple[str, str], set[str]] = {}
    for _, r in df.iterrows():
        region = str(r.get(region_col, "")).strip()
        comuna = str(r.get(comuna_col, "")).strip()
        dias = _decode_day_codes(str(r.get(dias_col, "")))
        if not region or not comuna or not dias:
            continue
        key = (_norm_text(region), _norm_text(comuna))
        out.setdefault(key, set()).update(dias)
    return out


def _read_fedex_frequencies_xlsx(path: Path) -> dict[tuple[str, str], set[str]]:
    out: dict[tuple[str, str], set[str]] = {}
    xls = pd.ExcelFile(path, engine="openpyxl")
    target_sheets = [s for s in xls.sheet_names if "frecuencia" in _norm_text(s)]

    for sh in target_sheets:
        try:
            df = pd.read_excel(path, sheet_name=sh, dtype=str, engine="openpyxl").fillna("")
        except Exception:
            continue

        # Formato observado: fila 0 header, fila 1 dias, fila >=2 datos.
        if len(df.columns) < 13 or len(df) < 3:
            continue

        for i in range(2, len(df)):
            region = str(df.iloc[i, 3]).strip()
            comuna = str(df.iloc[i, 5]).strip()
            if not region or not comuna:
                continue

            # Columnas 8..12 corresponden a L, M, X, J, V con marca "X".
            day_cells = [str(df.iloc[i, j]).strip().upper() for j in range(8, 13)]
            dias = []
            if day_cells[0] == "X":
                dias.append("Lunes")
            if day_cells[1] == "X":
                dias.append("Martes")
            if day_cells[2] == "X":
                dias.append("Miércoles")
            if day_cells[3] == "X":
                dias.append("Jueves")
            if day_cells[4] == "X":
                dias.append("Viernes")

            if not dias:
                continue
            key = (_norm_text(region), _norm_text(comuna))
            out.setdefault(key, set()).update(dias)

    return out


class SraMaryView(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sra Mary - Gestion de Despachos")
        self.geometry("1140x640")
        self.configure(bg="#F3F4F6")

        self.dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        self.vars_fedex = {dia: tk.BooleanVar() for dia in self.dias_semana}
        self.vars_urbano = {dia: tk.BooleanVar() for dia in self.dias_semana}
        self.datos = cargar_clientes()
        self.index_edicion: int | None = None

        self._crear_widgets()
        self._cargar_datos_en_tree()

    def _crear_widgets(self):
        frame_sup = tk.Frame(self, bg="#F3F4F6")
        frame_sup.pack(pady=5)

        tk.Label(frame_sup, text="Cliente:", bg="#F3F4F6").grid(row=0, column=0, padx=5)
        self.entry_cliente = tk.Entry(frame_sup, width=28)
        self.entry_cliente.grid(row=0, column=1, padx=5)

        tk.Label(frame_sup, text="Region:", bg="#F3F4F6").grid(row=0, column=2, padx=5)
        self.entry_region = tk.Entry(frame_sup, width=22)
        self.entry_region.grid(row=0, column=3, padx=5)

        tk.Label(frame_sup, text="Comuna:", bg="#F3F4F6").grid(row=0, column=4, padx=5)
        self.entry_comuna = tk.Entry(frame_sup, width=22)
        self.entry_comuna.grid(row=0, column=5, padx=5)

        tk.Label(frame_sup, text="Buscar:", bg="#F3F4F6").grid(row=1, column=0, padx=5, pady=(6, 0))
        self.entry_busqueda = tk.Entry(frame_sup, width=40)
        self.entry_busqueda.grid(row=1, column=1, columnspan=2, padx=5, pady=(6, 0), sticky="w")
        self.entry_busqueda.bind("<KeyRelease>", lambda e: self._filtrar_tree())

        frame_chk = tk.Frame(self, bg="#F3F4F6")
        frame_chk.pack(pady=10)

        frame_fedex = tk.LabelFrame(frame_chk, text="FedEx", bg="#F3F4F6", font=("Segoe UI", 10, "bold"))
        frame_fedex.grid(row=0, column=0, padx=30)
        for i, dia in enumerate(self.dias_semana):
            ttk.Checkbutton(frame_fedex, text=dia, variable=self.vars_fedex[dia]).grid(row=i, sticky="w")

        frame_urbano = tk.LabelFrame(frame_chk, text="Urbano", bg="#F3F4F6", font=("Segoe UI", 10, "bold"))
        frame_urbano.grid(row=0, column=1, padx=30)
        for i, dia in enumerate(self.dias_semana):
            ttk.Checkbutton(frame_urbano, text=dia, variable=self.vars_urbano[dia]).grid(row=i, sticky="w")

        frame_btns = tk.Frame(self, bg="#F3F4F6")
        frame_btns.pack(pady=5)
        ttk.Button(frame_btns, text="Guardar Cliente", command=self._guardar).grid(row=0, column=0, padx=5)
        ttk.Button(frame_btns, text="Actualizar Seleccion", command=self._actualizar).grid(row=0, column=1, padx=5)
        ttk.Button(frame_btns, text="Eliminar Seleccion", command=self._eliminar).grid(row=0, column=2, padx=5)
        ttk.Button(frame_btns, text="Importar Frecuencias", command=self._importar_frecuencias).grid(row=0, column=3, padx=5)

        self.tree = ttk.Treeview(
            self,
            columns=("Cliente", "Region", "Comuna", "FedEx", "Urbano"),
            show="headings",
            height=12,
        )
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            width = 220 if col in ("Cliente", "FedEx", "Urbano") else 170
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        self.tree.bind("<Double-1>", self._cargar_edicion)

    def _guardar(self):
        cliente = self.entry_cliente.get().strip()
        region = self.entry_region.get().strip()
        comuna = self.entry_comuna.get().strip()
        if not cliente:
            cliente = comuna or region
        if not cliente:
            return messagebox.showwarning("Falta Cliente", "Ingrese cliente o comuna.")

        dias_fedex = [d for d, v in self.vars_fedex.items() if v.get()]
        dias_urbano = [d for d, v in self.vars_urbano.items() if v.get()]
        if not dias_fedex and not dias_urbano:
            return messagebox.showwarning("Sin Dias", "Seleccione al menos un dia de despacho.")

        nuevo = {
            "cliente": cliente,
            "region": region,
            "comuna": comuna,
            "fedex_dias": dias_fedex,
            "urbano_dias": dias_urbano,
        }
        self.datos.append(nuevo)
        guardar_datos_json(self.datos)
        self._limpiar_formulario()
        self._cargar_datos_en_tree()

    def _cargar_datos_en_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.datos):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    item.get("cliente", ""),
                    item.get("region", ""),
                    item.get("comuna", ""),
                    ", ".join(item.get("fedex_dias", [])),
                    ", ".join(item.get("urbano_dias", [])),
                ),
            )

    def _filtrar_tree(self):
        termino = self.entry_busqueda.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.datos):
            hay = (
                termino in item.get("cliente", "").lower()
                or termino in item.get("region", "").lower()
                or termino in item.get("comuna", "").lower()
            )
            if not termino or hay:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        item.get("cliente", ""),
                        item.get("region", ""),
                        item.get("comuna", ""),
                        ", ".join(item.get("fedex_dias", [])),
                        ", ".join(item.get("urbano_dias", [])),
                    ),
                )

    def _cargar_edicion(self, _event):
        iid = self.tree.focus()
        if not iid:
            return
        index = int(iid)
        if index < 0 or index >= len(self.datos):
            return
        cliente = self.datos[index]
        self.index_edicion = index

        self.entry_cliente.delete(0, tk.END)
        self.entry_cliente.insert(0, cliente.get("cliente", ""))
        self.entry_region.delete(0, tk.END)
        self.entry_region.insert(0, cliente.get("region", ""))
        self.entry_comuna.delete(0, tk.END)
        self.entry_comuna.insert(0, cliente.get("comuna", ""))

        for dia in self.dias_semana:
            self.vars_fedex[dia].set(dia in cliente.get("fedex_dias", []))
            self.vars_urbano[dia].set(dia in cliente.get("urbano_dias", []))

    def _actualizar(self):
        if self.index_edicion is None:
            return messagebox.showwarning("Sin seleccion", "Debes seleccionar un cliente desde la lista.")

        cliente = self.entry_cliente.get().strip()
        region = self.entry_region.get().strip()
        comuna = self.entry_comuna.get().strip()
        if not cliente:
            cliente = comuna or region
        if not cliente:
            return messagebox.showwarning("Falta Cliente", "Ingrese cliente o comuna.")

        dias_fedex = [d for d, v in self.vars_fedex.items() if v.get()]
        dias_urbano = [d for d, v in self.vars_urbano.items() if v.get()]

        self.datos[self.index_edicion] = {
            "cliente": cliente,
            "region": region,
            "comuna": comuna,
            "fedex_dias": dias_fedex,
            "urbano_dias": dias_urbano,
        }

        guardar_datos_json(self.datos)
        self._limpiar_formulario()
        self._cargar_datos_en_tree()

    def _eliminar(self):
        iid = self.tree.focus()
        if not iid:
            return messagebox.showwarning("Sin seleccion", "Debes seleccionar un cliente para eliminar.")
        index = int(iid)
        if index < 0 or index >= len(self.datos):
            return

        cliente = self.datos[index].get("cliente", "")
        if messagebox.askyesno("Confirmar", f"Eliminar '{cliente}'?"):
            self.datos.pop(index)
            guardar_datos_json(self.datos)
            self._cargar_datos_en_tree()
            self._limpiar_formulario()

    def _limpiar_formulario(self):
        self.entry_cliente.delete(0, tk.END)
        self.entry_region.delete(0, tk.END)
        self.entry_comuna.delete(0, tk.END)
        for v in self.vars_fedex.values():
            v.set(False)
        for v in self.vars_urbano.values():
            v.set(False)
        self.index_edicion = None

    def _importar_frecuencias(self):
        try:
            desktop = Path.home() / "Desktop"
            transito = desktop / "transito.ods"
            fedex_files = list(desktop.glob("*Frecuencias*FedEx*.xlsx"))

            if not transito.exists():
                return messagebox.showwarning("Falta archivo", f"No se encontro: {transito}")
            if not fedex_files:
                return messagebox.showwarning("Falta archivo", "No se encontro archivo de Frecuencias FedEx en Desktop.")

            transito_map = _read_transito_ods(transito)
            fedex_map = _read_fedex_frequencies_xlsx(fedex_files[0])

            union: dict[tuple[str, str], set[str]] = {}
            for k, v in transito_map.items():
                union.setdefault(k, set()).update(v)
            for k, v in fedex_map.items():
                union.setdefault(k, set()).update(v)

            by_comuna: dict[str, set[str]] = {}
            for (_r, c), dias in union.items():
                by_comuna.setdefault(c, set()).update(dias)

            nuevos = []
            for (r, c), dias in transito_map.items():
                dias_final = set(dias)
                dias_final.update(union.get((r, c), set()))
                if not dias_final:
                    dias_final.update(by_comuna.get(c, set()))
                dias_sorted = [d for d in self.dias_semana if d in dias_final]
                if not dias_sorted:
                    continue

                region_txt = r.upper()
                comuna_txt = c.upper()
                nuevos.append(
                    {
                        "cliente": comuna_txt,
                        "region": region_txt,
                        "comuna": comuna_txt,
                        "fedex_dias": dias_sorted,
                        "urbano_dias": [],
                    }
                )

            idx = {
                (_norm_text(d.get("region", "")), _norm_text(d.get("comuna", ""))): i
                for i, d in enumerate(self.datos)
            }
            for n in nuevos:
                key = (_norm_text(n["region"]), _norm_text(n["comuna"]))
                if key in idx:
                    i = idx[key]
                    self.datos[i]["cliente"] = n["cliente"]
                    self.datos[i]["region"] = n["region"]
                    self.datos[i]["comuna"] = n["comuna"]
                    self.datos[i]["fedex_dias"] = n["fedex_dias"]
                else:
                    self.datos.append(n)

            guardar_datos_json(self.datos)
            self._cargar_datos_en_tree()
            messagebox.showinfo("Importacion OK", f"Se importaron/actualizaron {len(nuevos)} comunas.")
            logger.info(f"Sra Mary importo frecuencias. Procesadas: {len(nuevos)}")

        except Exception as e:
            logger.error(f"Error importando frecuencias: {e}")
            messagebox.showerror("Error", f"No se pudo importar frecuencias:\n{e}")
