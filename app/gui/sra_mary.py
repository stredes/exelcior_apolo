# Module: sra_mary.py
# Description: Gestion de clientes y dias de despacho preferidos para FedEx y Urbano.

from __future__ import annotations

import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import unicodedata
import re
from difflib import get_close_matches
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
from app.gui.etiqueta_editor import (
    CLIENTES_PATH_KEY,
    buscar_cliente_por_rut,
    cargar_clientes as cargar_clientes_excel,
    cargar_config as cargar_config_etiquetas,
)


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


def _norm_col(s: str) -> str:
    txt = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return txt.strip().lower().replace("_", " ")


def _find_col(cols_norm: dict[str, str], *names: str) -> str | None:
    for n in names:
        hit = cols_norm.get(_norm_col(n))
        if hit:
            return hit
    return None


def _buscar_cliente_por_nombre(df_clientes: pd.DataFrame | None, nombre: str) -> dict | None:
    if df_clientes is None or df_clientes.empty:
        return None
    term = _norm_text(nombre)
    if not term:
        return None

    cols_norm = {_norm_col(c): c for c in df_clientes.columns}
    col_nombre = _find_col(cols_norm, "razsoc", "razon social", "cliente", "nombre cliente", "nombre")
    col_dir = _find_col(cols_norm, "dir", "direccion", "domicilio")
    col_comuna = _find_col(cols_norm, "comuna")
    col_ciudad = _find_col(cols_norm, "ciudad")
    if not col_nombre:
        return None

    serie_nombre = df_clientes[col_nombre].astype(str).map(_norm_text)
    exact = df_clientes[serie_nombre == term]
    if not exact.empty:
        row = exact.iloc[0]
    else:
        mask = serie_nombre.str.contains(re.escape(term), na=False)
        if not mask.any():
            return None
        row = df_clientes[mask].iloc[0]

    return {
        "razsoc": row.get(col_nombre, "") if col_nombre else "",
        "dir": row.get(col_dir, "") if col_dir else "",
        "comuna": row.get(col_comuna, "") if col_comuna else "",
        "ciudad": row.get(col_ciudad, "") if col_ciudad else "",
    }


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
        self.geometry("1280x760")
        self.minsize(1140, 680)
        self.configure(bg="#EAF0F8")

        self.dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        self.vars_fedex = {dia: tk.BooleanVar() for dia in self.dias_semana}
        self.vars_urbano = {dia: tk.BooleanVar() for dia in self.dias_semana}
        self.datos = cargar_clientes()
        self.df_clientes_ref: pd.DataFrame | None = None
        self.clientes_nombre_cache: list[str] = []
        self.index_edicion: int | None = None
        self.status_var = tk.StringVar(value="Listo")
        self.sugerencias_var = tk.StringVar(value="")
        self._sugg_popup: tk.Toplevel | None = None
        self._sugg_listbox: tk.Listbox | None = None

        self._setup_style()
        self._crear_widgets()
        self._cargar_fuente_clientes()
        self._cargar_datos_en_tree()

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("SM.Bg.TFrame", background="#EAF0F8")
        style.configure("SM.Card.TFrame", background="#FFFFFF")
        style.configure("SM.Title.TLabel", background="#EAF0F8", foreground="#0D1D3A", font=("Segoe UI Semibold", 18))
        style.configure("SM.Sub.TLabel", background="#EAF0F8", foreground="#4B5F83", font=("Segoe UI", 10))
        style.configure("SM.Section.TLabelframe", background="#FFFFFF")
        style.configure("SM.Section.TLabelframe.Label", background="#FFFFFF", foreground="#1B2E52", font=("Segoe UI Semibold", 10))
        style.configure("SM.Body.TLabel", background="#FFFFFF", foreground="#1E2D4A", font=("Segoe UI", 10))
        style.configure("SM.Info.TLabel", background="#FFFFFF", foreground="#5A6E90", font=("Segoe UI", 9))
        style.configure("SM.Status.TLabel", background="#0F172A", foreground="#E2E8F0", font=("Segoe UI", 10), padding=8)
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _crear_widgets(self):
        shell = ttk.Frame(self, style="SM.Bg.TFrame", padding=14)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="Sra Mary", style="SM.Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Gestion de clientes y calendario de despacho", style="SM.Sub.TLabel").pack(anchor="w", pady=(2, 10))

        top_card = ttk.Frame(shell, style="SM.Card.TFrame", padding=12)
        top_card.pack(fill="x")
        # 4 bloques por fila: [label, entry] x 4
        for col in (1, 3, 5, 7):
            top_card.columnconfigure(col, weight=1)
        label_w = 13

        ttk.Label(top_card, text="RUT o Nombre", style="SM.Body.TLabel", width=label_w, anchor="e").grid(
            row=0, column=0, padx=(4, 6), pady=4, sticky="e"
        )
        self.entry_ref_cliente = ttk.Entry(top_card, width=30)
        self.entry_ref_cliente.grid(row=0, column=1, padx=(0, 10), pady=4, sticky="ew")
        self.entry_ref_cliente.bind("<Return>", self._cargar_cliente_desde_ref)
        self.entry_ref_cliente.bind("<KeyRelease>", self._on_ref_keyrelease)
        self.entry_ref_cliente.bind("<FocusOut>", lambda _e: self.after(180, self._hide_suggestions_popup))
        self.entry_ref_cliente.bind("<Down>", self._focus_suggestions)
        ttk.Button(top_card, text="Cargar Cliente", command=self._cargar_cliente_desde_ref).grid(
            row=0, column=2, padx=(0, 10), pady=4, sticky="w"
        )

        ttk.Label(top_card, text="Cliente", style="SM.Body.TLabel", width=label_w, anchor="e").grid(
            row=0, column=3, padx=(4, 6), pady=4, sticky="e"
        )
        self.entry_cliente = ttk.Entry(top_card, width=28)
        self.entry_cliente.grid(row=0, column=4, padx=(0, 10), pady=4, sticky="ew")
        self.entry_cliente.bind("<Return>", self._cargar_cliente_desde_ref)

        ttk.Label(top_card, text="Dirección", style="SM.Body.TLabel", width=label_w, anchor="e").grid(
            row=0, column=5, padx=(4, 6), pady=4, sticky="e"
        )
        self.entry_direccion = ttk.Entry(top_card, width=34)
        self.entry_direccion.grid(row=0, column=6, columnspan=2, padx=(0, 4), pady=4, sticky="ew")

        ttk.Label(top_card, text="Región", style="SM.Body.TLabel", width=label_w, anchor="e").grid(
            row=1, column=0, padx=(4, 6), pady=4, sticky="e"
        )
        self.entry_region = ttk.Entry(top_card, width=22)
        self.entry_region.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="ew")

        ttk.Label(top_card, text="Comuna", style="SM.Body.TLabel", width=label_w, anchor="e").grid(
            row=1, column=2, padx=(4, 6), pady=4, sticky="e"
        )
        self.entry_comuna = ttk.Entry(top_card, width=22)
        self.entry_comuna.grid(row=1, column=3, padx=(0, 10), pady=4, sticky="ew")

        ttk.Label(top_card, text="Buscar", style="SM.Body.TLabel", width=label_w, anchor="e").grid(
            row=1, column=4, padx=(4, 6), pady=4, sticky="e"
        )
        self.entry_busqueda = ttk.Entry(top_card, width=40)
        self.entry_busqueda.grid(row=1, column=5, columnspan=3, padx=(0, 4), pady=4, sticky="ew")
        self.entry_busqueda.bind("<KeyRelease>", lambda e: self._filtrar_tree())

        ttk.Label(top_card, textvariable=self.status_var, style="SM.Info.TLabel").grid(
            row=2, column=0, columnspan=7, sticky="w", padx=4, pady=(6, 0)
        )
        ttk.Label(top_card, textvariable=self.sugerencias_var, style="SM.Info.TLabel").grid(
            row=3, column=0, columnspan=7, sticky="w", padx=4, pady=(2, 0)
        )

        mid = ttk.Frame(shell, style="SM.Bg.TFrame")
        mid.pack(fill="x", pady=(10, 8))
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        frame_fedex = ttk.LabelFrame(mid, text="FedEx", padding=10, style="SM.Section.TLabelframe")
        frame_fedex.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame_urbano = ttk.LabelFrame(mid, text="Urbano", padding=10, style="SM.Section.TLabelframe")
        frame_urbano.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        for i, dia in enumerate(self.dias_semana):
            ttk.Checkbutton(frame_fedex, text=dia, variable=self.vars_fedex[dia]).grid(row=i, column=0, sticky="w", pady=1)
            ttk.Checkbutton(frame_urbano, text=dia, variable=self.vars_urbano[dia]).grid(row=i, column=0, sticky="w", pady=1)

        actions = ttk.Frame(shell, style="SM.Bg.TFrame")
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Guardar Cliente", command=self._guardar).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Actualizar Seleccion", command=self._actualizar).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Eliminar Seleccion", command=self._eliminar).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Importar Frecuencias", command=self._importar_frecuencias).pack(side="left")

        table_card = ttk.Frame(shell, style="SM.Card.TFrame", padding=8)
        table_card.pack(fill="both", expand=True)

        table_container = ttk.Frame(table_card, style="SM.Card.TFrame")
        table_container.pack(fill="both", expand=True)
        table_container.rowconfigure(0, weight=1)
        table_container.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_container,
            columns=("Cliente", "Direccion", "Region", "Comuna", "FedEx", "Urbano"),
            show="headings",
            height=14,
        )
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            width = 220 if col in ("Cliente", "FedEx", "Urbano") else (280 if col == "Direccion" else 170)
            self.tree.column(col, width=width, anchor="center")

        yscroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", self._cargar_edicion)

    def _cargar_fuente_clientes(self):
        try:
            cfg = cargar_config_etiquetas() or {}
            path = cfg.get(CLIENTES_PATH_KEY, "")
            if path and Path(path).exists():
                self.df_clientes_ref = cargar_clientes_excel(path)
                self.clientes_nombre_cache = self._extraer_nombres_clientes(self.df_clientes_ref)
                logger.info(f"Sra Mary: fuente de clientes cargada desde {path}")
            else:
                self.df_clientes_ref = None
                self.clientes_nombre_cache = []
        except Exception as e:
            logger.warning(f"Sra Mary: no se pudo cargar fuente de clientes: {e}")
            self.df_clientes_ref = None
            self.clientes_nombre_cache = []

    def _extraer_nombres_clientes(self, df_clientes: pd.DataFrame | None) -> list[str]:
        if df_clientes is None or df_clientes.empty:
            return []
        cols_norm = {_norm_col(c): c for c in df_clientes.columns}
        col_nombre = _find_col(cols_norm, "razsoc", "razon social", "cliente", "nombre cliente", "nombre")
        if not col_nombre:
            return []
        vals = [str(v).strip() for v in df_clientes[col_nombre].fillna("").tolist()]
        vals = [v for v in vals if v]
        seen = set()
        ordered = []
        for v in vals:
            k = _norm_text(v)
            if k and k not in seen:
                seen.add(k)
                ordered.append(v)
        return ordered

    def _sugerencias_por_nombre(self, query: str, limit: int = 6) -> list[str]:
        q = _norm_text(query)
        if not q or not self.clientes_nombre_cache:
            return []
        contains = [n for n in self.clientes_nombre_cache if q in _norm_text(n)]
        if contains:
            return contains[:limit]

        norm_to_original = {_norm_text(n): n for n in self.clientes_nombre_cache}
        close = get_close_matches(q, list(norm_to_original.keys()), n=limit, cutoff=0.55)
        return [norm_to_original[c] for c in close]

    def _hide_suggestions_popup(self):
        try:
            if self._sugg_popup and self._sugg_popup.winfo_exists():
                self._sugg_popup.destroy()
        except Exception:
            pass
        self._sugg_popup = None
        self._sugg_listbox = None

    def _show_suggestions_popup(self, items: list[str]):
        if not items:
            self._hide_suggestions_popup()
            return

        if self._sugg_popup and self._sugg_popup.winfo_exists() and self._sugg_listbox:
            self._sugg_listbox.delete(0, tk.END)
            for it in items:
                self._sugg_listbox.insert(tk.END, it)
            return

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.transient(self)
        popup.configure(bg="#A8B4C8")

        x = self.entry_ref_cliente.winfo_rootx()
        y = self.entry_ref_cliente.winfo_rooty() + self.entry_ref_cliente.winfo_height() + 2
        w = max(self.entry_ref_cliente.winfo_width(), 320)
        h = min(180, 30 * max(1, len(items)) + 4)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        lb = tk.Listbox(
            popup,
            font=("Segoe UI", 10),
            activestyle="none",
            selectmode=tk.SINGLE,
            relief="flat",
            borderwidth=0,
        )
        lb.pack(fill="both", expand=True, padx=1, pady=1)
        for it in items:
            lb.insert(tk.END, it)
        lb.selection_set(0)

        lb.bind("<Double-Button-1>", self._apply_selected_suggestion)
        lb.bind("<Return>", self._apply_selected_suggestion)
        lb.bind("<ButtonRelease-1>", self._apply_selected_suggestion)
        popup.bind("<FocusOut>", lambda _e: self.after(120, self._hide_suggestions_popup))

        self._sugg_popup = popup
        self._sugg_listbox = lb

    def _focus_suggestions(self, _event=None):
        if self._sugg_listbox and self._sugg_popup and self._sugg_popup.winfo_exists():
            self._sugg_listbox.focus_set()
            return "break"
        return None

    def _apply_selected_suggestion(self, _event=None):
        if not self._sugg_listbox:
            return
        sel = self._sugg_listbox.curselection()
        if not sel:
            return
        value = self._sugg_listbox.get(sel[0])
        self.entry_ref_cliente.delete(0, tk.END)
        self.entry_ref_cliente.insert(0, value)
        self._hide_suggestions_popup()
        self._cargar_cliente_desde_ref()

    def _on_ref_keyrelease(self, _event=None):
        query = self.entry_ref_cliente.get().strip()
        if not query:
            self.sugerencias_var.set("")
            self._hide_suggestions_popup()
            return
        # Si parece RUT, no mostrar sugerencias por nombre.
        if re.fullmatch(r"[0-9kK.\-]{6,20}", query):
            self.sugerencias_var.set("")
            self._hide_suggestions_popup()
            return
        sugeridas = self._sugerencias_por_nombre(query)
        if sugeridas:
            self.sugerencias_var.set("Aproximaciones: " + " | ".join(sugeridas))
            self._show_suggestions_popup(sugeridas)
        else:
            self.sugerencias_var.set("Sin aproximaciones para ese nombre.")
            self._hide_suggestions_popup()

    def _cargar_cliente_desde_ref(self, _event=None):
        if self.df_clientes_ref is None or self.df_clientes_ref.empty:
            self._cargar_fuente_clientes()
        if self.df_clientes_ref is None or self.df_clientes_ref.empty:
            messagebox.showwarning(
                "Fuente no disponible",
                "No se encontró el Excel de clientes. Cárgalo primero en la sección Etiquetas.",
            )
            return

        query = self.entry_ref_cliente.get().strip() or self.entry_cliente.get().strip()
        if not query:
            messagebox.showwarning("Dato faltante", "Ingresa RUT o nombre del cliente.")
            return

        cliente = buscar_cliente_por_rut(self.df_clientes_ref, query)
        if not cliente:
            cliente = _buscar_cliente_por_nombre(self.df_clientes_ref, query)
        if not cliente:
            sugeridas = self._sugerencias_por_nombre(query)
            if sugeridas:
                self.sugerencias_var.set("Aproximaciones: " + " | ".join(sugeridas))
                self._show_suggestions_popup(sugeridas)
                messagebox.showwarning(
                    "Sin coincidencia exacta",
                    "No se encontró coincidencia exacta.\n\nAproximaciones:\n- " + "\n- ".join(sugeridas),
                )
            else:
                self.sugerencias_var.set("Sin aproximaciones para ese nombre.")
                self._hide_suggestions_popup()
                messagebox.showwarning("Sin resultados", "No se encontró cliente con ese RUT o nombre.")
            return

        self.entry_cliente.delete(0, tk.END)
        self.entry_cliente.insert(0, str(cliente.get("razsoc", "")).strip())
        self.entry_direccion.delete(0, tk.END)
        self.entry_direccion.insert(0, str(cliente.get("dir", "")).strip())
        self.sugerencias_var.set("")
        self._hide_suggestions_popup()

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
            "direccion": self.entry_direccion.get().strip(),
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
                    item.get("direccion", ""),
                    item.get("region", ""),
                    item.get("comuna", ""),
                    ", ".join(item.get("fedex_dias", [])),
                    ", ".join(item.get("urbano_dias", [])),
                ),
            )
        self.status_var.set(f"Registros: {len(self.datos)}")

    def _filtrar_tree(self):
        termino = self.entry_busqueda.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        total = 0
        for idx, item in enumerate(self.datos):
            hay = (
                termino in item.get("cliente", "").lower()
                or termino in item.get("direccion", "").lower()
                or termino in item.get("region", "").lower()
                or termino in item.get("comuna", "").lower()
            )
            if not termino or hay:
                total += 1
                self.tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        item.get("cliente", ""),
                        item.get("direccion", ""),
                        item.get("region", ""),
                        item.get("comuna", ""),
                        ", ".join(item.get("fedex_dias", [])),
                        ", ".join(item.get("urbano_dias", [])),
                    ),
                )
        self.status_var.set(f"Registros filtrados: {total} de {len(self.datos)}")

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
        self.entry_direccion.delete(0, tk.END)
        self.entry_direccion.insert(0, cliente.get("direccion", ""))
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
            "direccion": self.entry_direccion.get().strip(),
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
        self.entry_ref_cliente.delete(0, tk.END)
        self.entry_cliente.delete(0, tk.END)
        self.entry_direccion.delete(0, tk.END)
        self.entry_region.delete(0, tk.END)
        self.entry_comuna.delete(0, tk.END)
        self.sugerencias_var.set("")
        self._hide_suggestions_popup()
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
