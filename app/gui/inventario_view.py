# app/gui/inventario_view.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict

import pandas as pd
import numpy as np

from app.services.inventory_difference_service import (
    close_inventory_difference_cycle,
    export_inventory_difference_report,
    get_inventory_difference_archive_dir,
    get_inventory_difference_output_dir,
    get_inventory_difference_summary,
    get_inventory_differences_df,
    merge_inventory_differences,
    remove_inventory_difference,
    save_inventory_difference,
)
from app.utils.utils import guardar_ultimo_path, load_config
from app.core.logger_eventos import capturar_log_bod1
from app.printer import printer_inventario_codigo, printer_inventario_ubicacion


# Columnas visibles y orden final en la grilla / impresion
BASE_INVENTORY_COLUMNS = [
    "Código", "Producto", "Bodega", "Ubicación",
    "N° Serie", "Lote", "Fecha Vencimiento", "Saldo Stock"
]
OPTIONAL_FILTER_COLUMNS = ["Subfamilia"]
VISIBLE_COLUMNS = BASE_INVENTORY_COLUMNS + ["Dif. Stock", "Stock Contado"]
TREE_COLUMNS = ["Sel"] + VISIBLE_COLUMNS

# Sinonimos (normalizados a minusculas y sin acentos) -> nombre objetivo
COL_SYNONYMS: Dict[str, str] = {
    "codigo": "Código",
    "código": "Código",
    "producto": "Producto",
    "descripcion": "Producto",
    "descripción": "Producto",
    "bodega": "Bodega",
    "ubicacion": "Ubicación",
    "ubicación": "Ubicación",
    "n serie": "N° Serie",
    "n° serie": "N° Serie",
    "numero serie": "N° Serie",
    "número serie": "N° Serie",
    "num serie": "N° Serie",
    "lote": "Lote",
    "fecha vencimiento": "Fecha Vencimiento",
    "fec venc": "Fecha Vencimiento",
    "vencimiento": "Fecha Vencimiento",
    "saldo stock": "Saldo Stock",
    "saldo": "Saldo Stock",
    "stock": "Saldo Stock",
    "subfamilia": "Subfamilia",
    "sub familia": "Subfamilia",
    "sub-familia": "Subfamilia",
}


def _norm_key(s: str) -> str:
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = " ".join(s.split())
    return s


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas usando COL_SYNONYMS y devuelve un DF con las visibles si existen."""
    mapping = {}
    for c in df.columns:
        key = _norm_key(str(c))
        if key in COL_SYNONYMS:
            mapping[c] = COL_SYNONYMS[key]
    out = df.rename(columns=mapping)

    def _try_pick(target: str, *candidates):
        if target in out.columns:
            return
        for cand in candidates:
            if cand in out.columns:
                out.rename(columns={cand: target}, inplace=True)
                return

    _try_pick("N° Serie", "N°Serie", "N Serie", "No Serie", "No. Serie")
    _try_pick("Saldo Stock", "Saldo stock", "Saldo  Stock")

    return out


def _clean_for_view(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia tipos/NaN para UI y posterior impresion."""
    df2 = df.copy()

    faltantes = [c for c in BASE_INVENTORY_COLUMNS if c not in df2.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {faltantes}")

    for c in ["Código", "Producto", "Bodega", "Ubicación", "N° Serie", "Lote"]:
        df2[c] = df2[c].astype(str).replace({"nan": "", "<NA>": ""}).fillna("").str.strip()

    if "Fecha Vencimiento" in df2.columns:
        dt = pd.to_datetime(df2["Fecha Vencimiento"], errors="coerce", dayfirst=True)
        df2["Fecha Vencimiento"] = np.where(
            dt.notna(),
            dt.dt.strftime("%d/%m/%Y"),
            df2["Fecha Vencimiento"].astype(str).replace({"nan": ""}).fillna(""),
        )

    df2["Saldo Stock"] = pd.to_numeric(df2["Saldo Stock"], errors="coerce").fillna(0).astype(int)

    mask_any = df2[BASE_INVENTORY_COLUMNS].astype(str).apply(lambda s: s.str.strip() != "").any(axis=1)
    output_columns = BASE_INVENTORY_COLUMNS + [c for c in OPTIONAL_FILTER_COLUMNS if c in df2.columns]
    for c in OPTIONAL_FILTER_COLUMNS:
        if c in df2.columns:
            df2[c] = df2[c].astype(str).replace({"nan": "", "<NA>": ""}).fillna("").str.strip()

    df2 = df2.loc[mask_any, output_columns].reset_index(drop=True)

    return df2


def _join_unique_values(series: pd.Series) -> str:
    values = []
    seen = set()
    for raw in series.fillna("").astype(str):
        value = raw.strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(value)
    return " | ".join(values)


def _is_bioplates_bodega(value: str) -> bool:
    text = _norm_key(value)
    return "bioplates" in text


class InventarioView(tk.Toplevel):
    PRODUCT_MIN_WIDTH = 280
    PRODUCT_MAX_WIDTH = 620
    DUPLICATE_DETAIL_COLUMNS = [
        "Código",
        "Producto",
        "Bodega",
        "Ubicación",
        "N° Serie",
        "Lote",
        "Fecha Vencimiento",
        "Saldo Stock",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventario - Consulta")
        self.geometry("1280x760")
        self.minsize(1080, 640)
        self.config(bg="#EEF2F8")
        self.resizable(True, True)
        try:
            self.attributes("-toolwindow", False)
        except Exception:
            pass

        self.df = pd.DataFrame()
        self.df_base = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.diff_df = pd.DataFrame()
        self.tipo_busqueda = None
        self.sort_column = None
        self.sort_ascending = True
        self.ubicaciones_disponibles = []
        self.ubicaciones_seleccionadas = set()
        self.ubicaciones_principales_seleccionadas = set()
        self.bodegas_disponibles = []
        self.subfamilias_disponibles = []
        self.selected_row_ids = set()
        self._ubic_popup = None
        self._archivo_actual = ""
        self.status_var = tk.StringVar(value="Carga un archivo de inventario para comenzar.")
        self.summary_var = tk.StringVar(value="Registros: 0")
        self.subfamilia_var = tk.StringVar(value="Todas")
        self.ubicaciones_var = tk.StringVar(value="Ubicaciones: todas")
        self.ubicaciones_principales_var = tk.StringVar(value="Ubicaciones: todas")
        self.printer_info_var = tk.StringVar(value="Impresora inventario: sin configurar")
        self.diff_cycle_var = tk.StringVar(value="Diferencias activas: 0")
        self.diff_archive_var = tk.StringVar(value="Historial de cierres: no disponible")
        self.bodega_var = tk.StringVar(value="Todas")
        self.stock_cero_var = tk.BooleanVar(value=False)

        self._crear_widgets()
        self._present_window()
        self._cargar_o_pedir_archivo()

    # ------------------------------- UI ---------------------------------

    def safe_messagebox(self, tipo, titulo, mensaje):
        self.after(
            0,
            lambda: {
                "info": messagebox.showinfo,
                "error": messagebox.showerror,
                "warning": messagebox.showwarning,
            }[tipo](titulo, mensaje, parent=self),
        )

    def _present_window(self):
        try:
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(350, lambda: self.attributes("-topmost", False))
            try:
                self.state("zoomed")
            except Exception:
                self.attributes("-zoomed", True)
        except Exception:
            pass

    def _crear_widgets(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("InvBg.TFrame", background="#EEF2F8")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("InvTitle.TLabel", font=("Segoe UI Semibold", 16), background="#EEF2F8", foreground="#0F1F3D")
        style.configure("InvSub.TLabel", font=("Segoe UI", 10), background="#EEF2F8", foreground="#485A79")
        style.configure("InvLabel.TLabel", font=("Segoe UI", 10), background="#FFFFFF", foreground="#263754")
        style.configure("InvHint.TLabel", font=("Segoe UI", 9), background="#FFFFFF", foreground="#5B6C89")
        style.configure("InvStatus.TLabel", font=("Segoe UI", 10), background="#0F172A", foreground="#E2E8F0", padding=8)
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10), background="#FFFFFF", fieldbackground="#FFFFFF", foreground="#14213D")
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI Semibold", 10),
            background="#DCE7F8",
            foreground="#0F1F3D",
            relief="solid",
            borderwidth=1,
            padding=(8, 6),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#C8DBF4")],
            foreground=[("active", "#0B1730")],
        )
        style.map("Treeview", background=[("selected", "#C9D8FF")], foreground=[("selected", "#0F1F3D")])

        shell = ttk.Frame(self, style="InvBg.TFrame", padding=14)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="Inventario", style="InvTitle.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Busqueda por texto, codigo, nombre, lote/serie, bodega y ubicacion fisica; tambien permite registrar diferencias de stock.", style="InvSub.TLabel").pack(anchor="w", pady=(2, 10))

        top_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
        top_card.pack(fill="x")

        filter_shell = ttk.Frame(top_card, style="Card.TFrame")
        filter_shell.pack(fill="x")

        search_block = ttk.LabelFrame(filter_shell, text="Busqueda", padding=10)
        search_block.pack(fill="x", pady=(0, 8))

        tk.Label(search_block, text="Buscar:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.entry_busqueda = tk.Entry(search_block, width=34, font=("Segoe UI", 10))
        self.entry_busqueda.grid(row=0, column=1, padx=(6, 12), sticky="w")
        self.entry_busqueda.bind("<Return>", lambda e: self._filtrar())
        self.entry_busqueda.bind("<KeyRelease>", lambda e: self._actualizar_sugerencias())

        tk.Label(search_block, text="Codigo producto:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
        self.entry_codigo = tk.Entry(search_block, width=18, font=("Segoe UI", 10))
        self.entry_codigo.grid(row=0, column=3, padx=(6, 12), sticky="w")
        self.entry_codigo.bind("<Return>", lambda e: self._filtrar())

        tk.Label(search_block, text="Bodega:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=4, sticky="w")
        self.combo_bodega = ttk.Combobox(search_block, textvariable=self.bodega_var, state="readonly", width=18)
        self.combo_bodega.grid(row=0, column=5, padx=(6, 12), sticky="w")
        self.combo_bodega.bind("<<ComboboxSelected>>", lambda e: self._filtrar())
        self.combo_bodega["values"] = ["Todas"]

        tk.Label(search_block, text="Lote / Serie:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.entry_lote_serie = tk.Entry(search_block, width=34, font=("Segoe UI", 10))
        self.entry_lote_serie.grid(row=1, column=1, padx=(6, 12), sticky="w", pady=(8, 0))
        self.entry_lote_serie.bind("<Return>", lambda e: self._filtrar())
        ttk.Label(
            search_block,
            textvariable=self.diff_cycle_var,
            style="InvLabel.TLabel",
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(
            search_block,
            text="Registrar diferencia",
            command=self._abrir_dialogo_diferencia,
        ).grid(row=1, column=4, sticky="w", pady=(8, 0), padx=(0, 8))
        ttk.Label(
            search_block,
            text="Selecciona una fila para guardar una diferencia positiva o negativa.",
            style="InvHint.TLabel",
        ).grid(row=1, column=5, sticky="w", pady=(8, 0))
        search_block.columnconfigure(6, weight=1)

        location_block = ttk.LabelFrame(filter_shell, text="Ubicacion Fisica", padding=10)
        location_block.pack(fill="x", pady=(0, 8))

        tk.Label(location_block, text="Ubicación principal:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.entry_ubicacion_selector = tk.Entry(location_block, width=12, font=("Segoe UI", 10))
        self.entry_ubicacion_selector.grid(row=0, column=1, padx=(6, 12), sticky="w")
        self.entry_ubicacion_selector.bind("<Return>", lambda e: self._seleccionar_por_ubicacion_principal())

        ttk.Button(location_block, text="Aplicar ubicación", command=self._seleccionar_por_ubicacion_principal).grid(row=0, column=2, padx=(0, 12), sticky="w")

        tk.Label(location_block, text="Fila:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=3, sticky="w")
        self.entry_fila_letra = tk.Entry(location_block, width=8, font=("Segoe UI", 10))
        self.entry_fila_letra.grid(row=0, column=4, padx=(6, 12), sticky="w")
        self.entry_fila_letra.bind("<Return>", lambda e: self._filtrar())

        tk.Label(location_block, text="Posición:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=5, sticky="w")
        self.entry_posicion = tk.Entry(location_block, width=8, font=("Segoe UI", 10))
        self.entry_posicion.grid(row=0, column=6, padx=(6, 12), sticky="w")
        self.entry_posicion.bind("<Return>", lambda e: self._filtrar())

        tk.Label(location_block, text="Subfamilia:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=7, sticky="w")
        self.combo_subfamilia = ttk.Combobox(location_block, textvariable=self.subfamilia_var, state="readonly", width=22)
        self.combo_subfamilia.grid(row=0, column=8, padx=(6, 12), sticky="w")
        self.combo_subfamilia.bind("<<ComboboxSelected>>", lambda e: self._filtrar())
        self.combo_subfamilia["values"] = ["Todas"]

        ttk.Checkbutton(location_block, text="Solo stock 0", variable=self.stock_cero_var, command=self._filtrar).grid(row=0, column=9, padx=(0, 12), sticky="w")
        ttk.Button(location_block, text="Ubicaciones ▼", command=self._abrir_selector_ubicaciones).grid(row=0, column=10, padx=(0, 6), sticky="w")
        ttk.Button(location_block, text="Ver ciclo activo", command=self._abrir_historial_diferencias).grid(row=0, column=11, padx=(10, 8), sticky="w")
        ttk.Label(
            location_block,
            textvariable=self.diff_archive_var,
            style="InvHint.TLabel",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=12, sticky="w")
        location_block.columnconfigure(12, weight=1)

        actions_block = ttk.LabelFrame(filter_shell, text="Acciones", padding=10)
        actions_block.pack(fill="x")
        ttk.Button(actions_block, text="Buscar", command=self._filtrar).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Limpiar", command=self._limpiar_busqueda).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Seleccionar todo", command=self._toggle_select_all).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Duplicados ubicación", command=self._mostrar_duplicados_ubicacion).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Abrir Excel", command=self._recargar_archivo).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Imprimir Resultado", command=self._imprimir_resultado).pack(side="left", padx=(0, 20))
        ttk.Button(actions_block, text="Exportar informe activo", command=self._exportar_informe_diferencias).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Cerrar ciclo diferencias", command=self._cerrar_ciclo_diferencias).pack(side="left")

        info_row = ttk.Frame(top_card, style="Card.TFrame")
        info_row.pack(fill="x", pady=(12, 0))
        ttk.Label(info_row, textvariable=self.summary_var, style="InvLabel.TLabel").pack(side="left")
        ttk.Label(info_row, textvariable=self.ubicaciones_principales_var, style="InvLabel.TLabel").pack(side="left", padx=(16, 0))
        ttk.Label(info_row, textvariable=self.ubicaciones_var, style="InvLabel.TLabel").pack(side="left", padx=(16, 0))
        ttk.Label(info_row, textvariable=self.printer_info_var, style="InvLabel.TLabel").pack(side="left", padx=(16, 0))
        ttk.Label(info_row, textvariable=self.status_var, style="InvHint.TLabel").pack(side="left", padx=(16, 0))

        self.sugerencias_var = tk.StringVar(value="")
        ttk.Label(shell, textvariable=self.sugerencias_var, style="InvSub.TLabel").pack(anchor="w", padx=2, pady=(8, 4))

        table_card = ttk.Frame(shell, style="Card.TFrame", padding=8)
        table_card.pack(fill="both", expand=True, pady=(0, 8))

        tree_container = ttk.Frame(table_card, style="Card.TFrame")
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_container, columns=TREE_COLUMNS, show="headings", height=25)
        self.tree["displaycolumns"] = TREE_COLUMNS
        self._configure_tree_columns()

        yscroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)
        self.tree.bind("<Button-1>", self._on_tree_click)

        status_bar = ttk.Frame(shell, style="InvBg.TFrame")
        status_bar.pack(fill="x")
        ttk.Label(status_bar, textvariable=self.summary_var, style="InvStatus.TLabel").pack(fill="x")

    def _actualizar_sugerencias(self):
        term_raw = self.entry_busqueda.get()
        if not term_raw or self.df.empty:
            self.sugerencias_var.set("")
            return
        terminos = [self._norm_text(t) for t in term_raw.replace(",", " ").split() if t.strip()]
        ubicaciones = self.df["Ubicación"].dropna().unique()
        sugeridas = [u for u in ubicaciones if all(t in self._norm_text(u) for t in terminos)]
        if sugeridas:
            suf = " ..." if len(sugeridas) > 8 else ""
            self.sugerencias_var.set("Coincidencias: " + ", ".join(sugeridas[:8]) + suf)
        else:
            self.sugerencias_var.set("Sin coincidencias")

    # ---------------------------- Carga Excel ----------------------------

    def _cargar_o_pedir_archivo(self):
        config = load_config() or {}
        self._actualizar_info_impresora(config)
        ruta = config.get("archivo_inventario")
        if ruta and Path(ruta).exists():
            self._leer_excel(Path(ruta))
        else:
            self._buscar_y_cargar_archivo()

    def _recargar_archivo(self):
        self._buscar_y_cargar_archivo()

    def _buscar_y_cargar_archivo(self):
        ruta_archivo = filedialog.askopenfilename(
            parent=self,
            title="Selecciona el archivo de inventario",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")],
        )
        if ruta_archivo:
            guardar_ultimo_path(ruta_archivo, clave="archivo_inventario")
            self._leer_excel(Path(ruta_archivo))

    def _leer_excel(self, path: Path):
        try:
            suffix = path.suffix.lower()
            if suffix == ".xlsx":
                df = pd.read_excel(path, engine="openpyxl")
            elif suffix == ".xls":
                try:
                    df = pd.read_excel(path, engine="xlrd")
                except ImportError:
                    raise RuntimeError(
                        "Missing optional dependency 'xlrd'. Instala xlrd >= 2.0.1 para abrir archivos .xls "
                        "o guarda el archivo como .xlsx e intentalo nuevamente."
                    )
            else:
                raise ValueError("Extension de archivo no soportada. Usa .xlsx o .xls")

            df = _normalize_headers(df)
            df = _clean_for_view(df)

            self.df_base = df
            self.diff_df = get_inventory_differences_df()
            self._actualizar_resumen_diferencias()
            self.df = merge_inventory_differences(self.df_base, self.diff_df)
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self.sort_column = None
            self.sort_ascending = True
            self.ubicaciones_disponibles = sorted(df["Ubicación"].dropna().astype(str).str.strip().unique().tolist())
            self.ubicaciones_seleccionadas = set()
            self.ubicaciones_principales_seleccionadas = set()
            self.subfamilias_disponibles = self._extraer_valores_unicos(df, "Subfamilia")
            self.combo_subfamilia["values"] = ["Todas"] + self.subfamilias_disponibles
            self.subfamilia_var.set("Todas")
            self.combo_subfamilia.configure(state="readonly" if self.subfamilias_disponibles else "disabled")
            self.bodegas_disponibles = sorted(df["Bodega"].dropna().astype(str).str.strip().unique().tolist())
            self.combo_bodega["values"] = ["Todas"] + self.bodegas_disponibles
            self.combo_bodega.current(0)
            self.selected_row_ids = set()
            self._actualizar_label_ubicaciones_principales()
            self._actualizar_label_ubicaciones()
            self._actualizar_info_impresora(load_config() or {})
            self._archivo_actual = path.name
            self._actualizar_tree(self.df)
            self.status_var.set(f"Archivo cargado: {path.name}")
            self.entry_busqueda.focus_set()
            self.after(50, self._present_window)

            capturar_log_bod1(f"[Inventario] Archivo cargado: {path}", "info")
            self.safe_messagebox("info", "Inventario", f"Archivo cargado correctamente: {path.name}")

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al cargar inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo cargar el archivo:\n{e}")
            self.df = pd.DataFrame()
            self.df_base = pd.DataFrame()
            self.df_filtrado = pd.DataFrame()
            self.diff_df = pd.DataFrame()
            self._actualizar_resumen_diferencias()
            self.tipo_busqueda = None
            self.sort_column = None
            self.sort_ascending = True
            self.ubicaciones_disponibles = []
            self.ubicaciones_seleccionadas = set()
            self.ubicaciones_principales_seleccionadas = set()
            self.subfamilias_disponibles = []
            self.combo_subfamilia["values"] = ["Todas"]
            self.subfamilia_var.set("Todas")
            self.combo_subfamilia.configure(state="disabled")
            self.bodegas_disponibles = []
            self.combo_bodega["values"] = ["Todas"]
            self.bodega_var.set("Todas")
            self.selected_row_ids = set()
            self._actualizar_label_ubicaciones_principales()
            self._actualizar_label_ubicaciones()
            self._actualizar_info_impresora(load_config() or {})
            self._archivo_actual = ""
            self.status_var.set("No se pudo cargar el archivo.")
            self._actualizar_tree(self.df)

    # ----------------------------- Busqueda ------------------------------

    def _norm_text(self, s: str) -> str:
        s = str(s or "").strip().lower()
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return " ".join(s.split())

    def _extraer_valores_unicos(self, df: pd.DataFrame, column: str) -> list[str]:
        if df is None or df.empty or column not in df.columns:
            return []
        values = []
        seen = set()
        for raw in df[column].dropna().astype(str):
            value = raw.strip()
            key = self._norm_text(value)
            if not value or key in seen:
                continue
            seen.add(key)
            values.append(value)
        return sorted(values, key=self._norm_text)

    def _filtrar(self, silent_no_filters: bool = False):
        term_raw = self.entry_busqueda.get()
        codigo_producto = self._norm_text(self.entry_codigo.get())
        lote_serie = self._norm_text(self.entry_lote_serie.get())
        ubicaciones_principales = self._parse_selector_tokens(self.entry_ubicacion_selector.get())
        self.ubicaciones_principales_seleccionadas = set(ubicaciones_principales)
        self._actualizar_label_ubicaciones_principales()
        bodega = self._norm_text(self.bodega_var.get())
        subfamilia = self._norm_text(self.subfamilia_var.get())
        fila_letra = self._norm_text(self.entry_fila_letra.get())
        posicion = self._norm_text(self.entry_posicion.get())
        solo_stock_cero = bool(self.stock_cero_var.get())

        if not term_raw.strip() and not codigo_producto and not lote_serie and subfamilia in ("", "todas") and not ubicaciones_principales and not fila_letra and not posicion and not self.ubicaciones_seleccionadas and bodega in ("", "todas") and not solo_stock_cero:
            if not silent_no_filters:
                self.safe_messagebox("info", "Buscar", "Ingrese un termino, codigo de producto, lote/serie, subfamilia, ubicacion principal, fila, posicion, bodega, stock 0 o seleccione ubicaciones.")
            return
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        df = self.df.copy()
        terminos = [self._norm_text(t) for t in term_raw.replace(",", " ").split() if t.strip()]

        m_ubi = df["Ubicación"].astype(str).map(self._norm_text)
        m_cod = df["Código"].astype(str).map(self._norm_text)
        m_prod = df["Producto"].astype(str).map(self._norm_text)
        m_lote = df["Lote"].astype(str).map(self._norm_text)
        m_serie = df["N° Serie"].astype(str).map(self._norm_text)
        m_bodega = df["Bodega"].astype(str).map(self._norm_text)
        m_subfamilia = df["Subfamilia"].astype(str).map(self._norm_text) if "Subfamilia" in df.columns else pd.Series([""] * len(df), index=df.index)
        m_ubicacion_principal = df["Ubicación"].astype(str).map(self._extract_main_row)

        if terminos:
            mask_ubi = m_ubi.apply(lambda val: all(term in val for term in terminos))
            mask_cod = m_cod.apply(lambda val: all(term in val for term in terminos))
            mask_prod = m_prod.apply(lambda val: all(term in val for term in terminos))
            mask_lote = m_lote.apply(lambda val: all(term in val for term in terminos))
            mask_serie = m_serie.apply(lambda val: all(term in val for term in terminos))
            mask_texto = mask_ubi | mask_cod | mask_prod | mask_lote | mask_serie
        else:
            mask_ubi = pd.Series([False] * len(df), index=df.index)
            mask_cod = pd.Series([False] * len(df), index=df.index)
            mask_prod = pd.Series([False] * len(df), index=df.index)
            mask_lote = pd.Series([False] * len(df), index=df.index)
            mask_serie = pd.Series([False] * len(df), index=df.index)
            mask_texto = pd.Series([True] * len(df), index=df.index)

        mask_fila_letra = pd.Series([True] * len(df), index=df.index)
        if fila_letra:
            mask_fila_letra = df["Ubicación"].astype(str).apply(lambda val: self._location_row_matches(val, fila_letra))

        mask_posicion = pd.Series([True] * len(df), index=df.index)
        if posicion:
            mask_posicion = df["Ubicación"].astype(str).apply(lambda val: self._location_position_matches(val, posicion))

        mask_codigo_directo = pd.Series([True] * len(df), index=df.index)
        if codigo_producto:
            mask_codigo_directo = m_cod.apply(lambda val: codigo_producto in val)

        mask_lote_serie = pd.Series([True] * len(df), index=df.index)
        if lote_serie:
            mask_lote_serie = m_lote.apply(lambda val: lote_serie in val) | m_serie.apply(lambda val: lote_serie in val)

        mask_ubicacion_principal = pd.Series([True] * len(df), index=df.index)
        if ubicaciones_principales:
            mask_ubicacion_principal = m_ubicacion_principal.isin(ubicaciones_principales)

        mask_bodega = pd.Series([True] * len(df), index=df.index)
        if bodega and bodega != "todas":
            mask_bodega = m_bodega == bodega

        mask_subfamilia = pd.Series([True] * len(df), index=df.index)
        if subfamilia and subfamilia != "todas":
            mask_subfamilia = m_subfamilia == subfamilia

        mask_stock_cero = pd.Series([True] * len(df), index=df.index)
        if solo_stock_cero:
            stock_values = pd.to_numeric(df["Saldo Stock"], errors="coerce").fillna(0)
            mask_stock_cero = stock_values <= 0

        mask_sel_ubic = pd.Series([True] * len(df), index=df.index)
        if self.ubicaciones_seleccionadas:
            sel_norm = {self._norm_text(v) for v in self.ubicaciones_seleccionadas}
            mask_sel_ubic = m_ubi.isin(sel_norm)

        mask_total = mask_texto & mask_codigo_directo & mask_lote_serie & mask_ubicacion_principal & mask_bodega & mask_subfamilia & mask_stock_cero & mask_fila_letra & mask_posicion & mask_sel_ubic

        if mask_total.any():
            self.df_filtrado = df.loc[mask_total].reset_index(drop=True)
            location_filter_active = bool(ubicaciones_principales or fila_letra or posicion or self.ubicaciones_seleccionadas)
            if location_filter_active:
                self.df_filtrado = self._sorted_dataframe(self.df_filtrado, "Ubicación", True).reset_index(drop=True)
                self.sort_column = "Ubicación"
                self.sort_ascending = True
            if codigo_producto:
                self.tipo_busqueda = "codigo"
            elif lote_serie:
                self.tipo_busqueda = "lote_serie"
            elif self.ubicaciones_seleccionadas or ubicaciones_principales or bodega not in ("", "todas") or subfamilia not in ("", "todas") or solo_stock_cero or fila_letra or posicion or mask_ubi.any():
                self.tipo_busqueda = "ubicacion"
            elif mask_cod.any():
                self.tipo_busqueda = "codigo"
            elif mask_prod.any() or mask_lote.any() or mask_serie.any():
                self.tipo_busqueda = "producto"
            else:
                self.tipo_busqueda = None
            if ubicaciones_principales:
                self.status_var.set(
                    f"Ubicaciones {', '.join(sorted(ubicaciones_principales))}: {len(self.df_filtrado)} productos en {self.df_filtrado['Ubicación'].nunique()} posiciones."
                )
            else:
                self.status_var.set(f"Filtro aplicado. Resultados: {len(self.df_filtrado)}")
        else:
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self.status_var.set("Sin resultados para el filtro aplicado.")

        self.selected_row_ids = set()
        self._actualizar_tree(self.df_filtrado)
        self._actualizar_sugerencias()

    def _limpiar_busqueda(self):
        self.entry_busqueda.delete(0, "end")
        self.entry_codigo.delete(0, "end")
        self.entry_lote_serie.delete(0, "end")
        self.entry_ubicacion_selector.delete(0, "end")
        self.bodega_var.set("Todas")
        self.subfamilia_var.set("Todas")
        self.stock_cero_var.set(False)
        self.entry_fila_letra.delete(0, "end")
        self.entry_posicion.delete(0, "end")
        self.df_filtrado = pd.DataFrame()
        self.tipo_busqueda = None
        self.ubicaciones_principales_seleccionadas = set()
        self.ubicaciones_seleccionadas = set()
        self.selected_row_ids = set()
        self._actualizar_label_ubicaciones_principales()
        self._actualizar_label_ubicaciones()
        self.sugerencias_var.set("")
        self.status_var.set("Filtros limpiados.")
        self._actualizar_tree(self.df)

    def _build_duplicate_locations_report(self, source_df: pd.DataFrame) -> pd.DataFrame:
        if source_df is None or source_df.empty:
            return pd.DataFrame(columns=VISIBLE_COLUMNS)

        base = source_df.loc[
            ~source_df["Bodega"].fillna("").astype(str).map(_is_bioplates_bodega)
        ].copy()
        if base.empty:
            return pd.DataFrame(columns=VISIBLE_COLUMNS)

        base["__ubic_count"] = (
            base["Ubicación"]
            .fillna("")
            .astype(str)
            .str.strip()
            .groupby([base["Código"], base["Producto"]])
            .transform(lambda s: s[s != ""].nunique())
        )

        duplicates = base.loc[base["__ubic_count"] > 1].copy()
        if duplicates.empty:
            return pd.DataFrame(columns=VISIBLE_COLUMNS)

        report = (
            duplicates.groupby(["Código", "Producto"], as_index=False)
            .agg(
                {
                    "Bodega": _join_unique_values,
                    "Ubicación": _join_unique_values,
                    "N° Serie": _join_unique_values,
                    "Lote": _join_unique_values,
                    "Fecha Vencimiento": _join_unique_values,
                    "Saldo Stock": "sum",
                }
            )
        )

        report["Saldo Stock"] = pd.to_numeric(report["Saldo Stock"], errors="coerce").fillna(0).astype(int)
        report = merge_inventory_differences(report.loc[:, BASE_INVENTORY_COLUMNS].reset_index(drop=True), self.diff_df)
        return report.loc[:, VISIBLE_COLUMNS].reset_index(drop=True)

    def _mostrar_duplicados_ubicacion(self):
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        source_df = self._current_view_df()
        detail_df = self._build_duplicate_locations_detail(source_df)
        self.selected_row_ids = set()
        if detail_df.empty:
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = "duplicados"
            self._actualizar_tree(self.df_filtrado)
            self.status_var.set("No se encontraron productos con más de una ubicación en la vista actual.")
            self.safe_messagebox("info", "Duplicados", "No se encontraron productos con más de una ubicación.")
            return

        self.df_filtrado = detail_df
        self.tipo_busqueda = "duplicados"
        self._actualizar_tree(self.df_filtrado)
        total_productos = detail_df.groupby(["Código", "Producto"]).ngroups
        self.status_var.set(
            f"Listado de duplicados generado: {total_productos} productos con más de una ubicación."
        )
        capturar_log_bod1(
            f"[Inventario] Listado de duplicados por ubicación generado con {total_productos} productos.",
            "info",
        )

    def _build_duplicate_locations_detail(self, source_df: pd.DataFrame) -> pd.DataFrame:
        if source_df is None or source_df.empty:
            return pd.DataFrame(columns=VISIBLE_COLUMNS)

        base = source_df.loc[
            ~source_df["Bodega"].fillna("").astype(str).map(_is_bioplates_bodega)
        ].copy()
        if base.empty:
            return pd.DataFrame(columns=VISIBLE_COLUMNS)

        duplicate_counts = (
            base.assign(__ubic_clean=base["Ubicación"].fillna("").astype(str).str.strip())
            .groupby(["Código", "Producto"])["__ubic_clean"]
            .transform(lambda s: s[s != ""].nunique())
        )
        detail = base.loc[duplicate_counts > 1, VISIBLE_COLUMNS].copy()
        if detail.empty:
            return pd.DataFrame(columns=VISIBLE_COLUMNS)

        detail["__fecha_sort"] = pd.to_datetime(detail["Fecha Vencimiento"], format="%d/%m/%Y", errors="coerce")
        detail = detail.sort_values(
            by=["Código", "Producto", "Ubicación", "__fecha_sort", "Lote", "N° Serie"],
            kind="mergesort",
        ).drop(columns=["__fecha_sort"])
        return detail.reset_index(drop=True)

    def _sort_by_column(self, column: str):
        if self.df.empty:
            return

        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True

        target_df = self.df_filtrado if not self.df_filtrado.empty else self.df
        if target_df.empty or column not in target_df.columns:
            return

        sorted_df = self._sorted_dataframe(target_df, column, self.sort_ascending)
        if not self.df_filtrado.empty:
            self.df_filtrado = sorted_df.reset_index(drop=True)
            self._actualizar_tree(self.df_filtrado)
        else:
            self.df = sorted_df.reset_index(drop=True)
            self._actualizar_tree(self.df)

    def _sorted_dataframe(self, df: pd.DataFrame, column: str, ascending: bool) -> pd.DataFrame:
        s = df[column]
        if self._is_location_column(column):
            sorted_index = sorted(
                df.index,
                key=lambda idx: self._location_sort_key(df.at[idx, column]),
                reverse=not ascending,
            )
            return df.loc[sorted_index]

        numeric = pd.to_numeric(s, errors="coerce")
        if numeric.notna().any():
            return df.assign(__sort_key=numeric).sort_values(
                by="__sort_key",
                ascending=ascending,
                na_position="last",
                kind="mergesort",
            ).drop(columns=["__sort_key"])

        if column == "Fecha Vencimiento":
            dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
            if dt.notna().any():
                return df.assign(__sort_key=dt).sort_values(
                    by="__sort_key",
                    ascending=ascending,
                    na_position="last",
                    kind="mergesort",
                ).drop(columns=["__sort_key"])

        txt = s.astype(str).map(self._norm_text)
        return df.assign(__sort_key=txt).sort_values(
            by="__sort_key",
            ascending=ascending,
            na_position="last",
            kind="mergesort",
        ).drop(columns=["__sort_key"])

    # --------------------------- Actualizar UI ---------------------------

    def _actualizar_tree(self, df: pd.DataFrame):
        self._update_heading_texts()
        self.tree.delete(*self.tree.get_children())
        if df is None or df.empty:
            self.summary_var.set("Registros: 0")
            self._autoajustar_columna_producto()
            return

        if self.tipo_busqueda == "duplicados":
            self._actualizar_tree_duplicados(df)
            return

        for i, row in enumerate(df[VISIBLE_COLUMNS].itertuples(index=False)):
            tag = "even" if i % 2 == 0 else "odd"
            marker = "☑" if i in self.selected_row_ids else "☐"
            self.tree.insert("", "end", iid=str(i), values=(marker, *row), tags=(tag,))

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F6F8FD")
        self._autoajustar_columna_producto(df)
        origen = self._archivo_actual or "sin archivo"
        self.summary_var.set(f"Registros: {len(df)} | Fuente: {origen}")

    def _actualizar_tree_duplicados(self, df: pd.DataFrame):
        row_index = 0
        total_productos = df.groupby(["Código", "Producto"]).ngroups if not df.empty else 0
        for (codigo, producto), group in df.groupby(["Código", "Producto"], sort=False):
            total_stock = int(pd.to_numeric(group["Saldo Stock"], errors="coerce").fillna(0).sum())
            ubic_count = group["Ubicación"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
            resumen = f"Producto con {ubic_count} ubicaciones"
            self.tree.insert(
                "",
                "end",
                iid=f"group-{row_index}",
                values=("", codigo, producto, "", resumen, "", "", "", total_stock, 0, total_stock),
                tags=("group",),
            )
            row_index += 1

            for data_index, row in group.iterrows():
                tag = "even" if row_index % 2 == 0 else "odd"
                marker = "☑" if data_index in self.selected_row_ids else "☐"
                self.tree.insert(
                    "",
                    "end",
                    iid=f"data-{data_index}",
                    values=(marker, *(row[col] for col in VISIBLE_COLUMNS)),
                    tags=(tag,),
                )
                row_index += 1

        self.tree.tag_configure("group", background="#DCE7F8", font=("Segoe UI Semibold", 10))
        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F6F8FD")
        self._autoajustar_columna_producto(df)
        origen = self._archivo_actual or "sin archivo"
        self.summary_var.set(
            f"Duplicados: {total_productos} productos | Registros: {len(df)} | Fuente: {origen}"
        )

    def _configure_tree_columns(self):
        self.tree.heading("Sel", text="Sel", anchor="center", command=self._toggle_select_all)
        self.tree.column("Sel", width=52, minwidth=52, anchor="center", stretch=False)
        for col in VISIBLE_COLUMNS:
            self.tree.heading(col, text=col, anchor="center", command=lambda c=col: self._sort_by_column(c))
            width = 140
            if col == "Producto":
                width = 280
            elif col in ("Bodega", "Ubicación"):
                width = 160
            elif col in ("Fecha Vencimiento", "Saldo Stock", "Stock Contado"):
                width = 130
            elif col == "Dif. Stock":
                width = 110
            self.tree.column(col, width=width, minwidth=110, anchor="center", stretch=True)
        self._update_heading_texts()

    def _autoajustar_columna_producto(self, df: pd.DataFrame | None = None):
        try:
            font = tkfont.nametofont(str(self.tree.cget("font")))
        except Exception:
            font = tkfont.Font(family="Segoe UI", size=10)

        width_px = font.measure("Producto") + 36
        source_df = df if df is not None and not df.empty else self._current_view_df()
        if source_df is not None and not source_df.empty and "Producto" in source_df.columns:
            muestras = source_df["Producto"].astype(str).fillna("").head(300)
            for value in muestras:
                width_px = max(width_px, font.measure(value) + 36)

        width_px = max(self.PRODUCT_MIN_WIDTH, min(width_px, self.PRODUCT_MAX_WIDTH))
        self.tree.column("Producto", width=width_px)

    def _current_view_df(self) -> pd.DataFrame:
        return self.df_filtrado if not self.df_filtrado.empty else self.df

    def _current_print_df(self) -> pd.DataFrame:
        current = self._current_view_df()
        if current is None or current.empty:
            return pd.DataFrame(columns=BASE_INVENTORY_COLUMNS)
        return current.loc[:, BASE_INVENTORY_COLUMNS].reset_index(drop=True)

    def _selected_view_df(self) -> pd.DataFrame:
        current = self._current_view_df()
        if current is None or current.empty or not self.selected_row_ids:
            return pd.DataFrame()
        valid_indexes = [idx for idx in sorted(self.selected_row_ids) if 0 <= idx < len(current)]
        if not valid_indexes:
            return pd.DataFrame()
        return current.iloc[valid_indexes].reset_index(drop=True)

    def _selected_print_df(self) -> pd.DataFrame:
        current = self._current_print_df()
        if current is None or current.empty or not self.selected_row_ids:
            return pd.DataFrame(columns=BASE_INVENTORY_COLUMNS)
        valid_indexes = [idx for idx in sorted(self.selected_row_ids) if 0 <= idx < len(current)]
        if not valid_indexes:
            return pd.DataFrame(columns=BASE_INVENTORY_COLUMNS)
        return current.iloc[valid_indexes].reset_index(drop=True)

    def _toggle_select_all(self):
        current = self._current_view_df()
        if current is None or current.empty:
            self.safe_messagebox("info", "Inventario", "No hay registros visibles para seleccionar.")
            return
        if len(self.selected_row_ids) == len(current):
            self.selected_row_ids.clear()
            self.status_var.set("Seleccion completa limpiada.")
        else:
            self.selected_row_ids = set(range(len(current)))
            self.status_var.set(f"Seleccionados {len(self.selected_row_ids)} registros visibles.")
        self._actualizar_tree(current)

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if region == "cell" and column == "#1" and row_id:
            if row_id.startswith("group-"):
                return "break"
            if row_id.startswith("data-"):
                idx = int(row_id.split("-", 1)[1])
            else:
                try:
                    idx = int(row_id)
                except (TypeError, ValueError):
                    return "break"
            if idx in self.selected_row_ids:
                self.selected_row_ids.remove(idx)
            else:
                self.selected_row_ids.add(idx)
            self._actualizar_tree(self._current_view_df())
            return "break"

    def _update_heading_texts(self):
        self.tree.heading("Sel", text="Sel", anchor="center", command=self._toggle_select_all)
        for col in VISIBLE_COLUMNS:
            arrow = ""
            if self.sort_column == col:
                arrow = " ▲" if self.sort_ascending else " ▼"
            self.tree.heading(col, text=f"{col}{arrow}", anchor="center", command=lambda c=col: self._sort_by_column(c))

    # ------------------------------ Print -------------------------------

    def _imprimir_resultado(self):
        df_selected = self._selected_print_df()
        df_to_print = df_selected if not df_selected.empty else self._current_print_df()
        if df_to_print.empty:
            self.safe_messagebox("warning", "Sin datos", "No hay datos para imprimir.")
            return

        try:
            cfg = load_config() or {}
            inventory_printer = self._get_inventory_printer_name(cfg)
            self._actualizar_info_impresora(cfg)
            capturar_log_bod1(
                f"[Inventario] Impresion solicitada (tipo={self.tipo_busqueda or 'completo'}) "
                f"con {len(df_to_print)} registros. Impresora: {inventory_printer or 'predeterminada SO'}.",
                "info",
            )

            if self.tipo_busqueda == "ubicacion":
                printer_inventario_ubicacion.print_inventario_ubicacion(
                    file_path=self._archivo_actual or "inventario.xlsx",
                    config={"printer_name": inventory_printer, "inventory_print_mode": self.tipo_busqueda or ""},
                    df=df_to_print,
                )
            else:
                printer_inventario_codigo.print_inventario_codigo(
                    file_path=self._archivo_actual or "inventario.xlsx",
                    config={"printer_name": inventory_printer, "inventory_print_mode": self.tipo_busqueda or ""},
                    df=df_to_print,
                )

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al imprimir inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo imprimir:\n{e}")

    def _refresh_differences_and_view(self):
        self.diff_df = get_inventory_differences_df()
        self._actualizar_resumen_diferencias()
        if self.df_base is not None and not self.df_base.empty:
            self.df = merge_inventory_differences(self.df_base, self.diff_df)
        else:
            self.df = pd.DataFrame()

        if self._has_active_filters():
            self._filtrar(silent_no_filters=True)
        else:
            self.df_filtrado = pd.DataFrame()
            self._actualizar_tree(self.df)

    def _actualizar_resumen_diferencias(self):
        summary = get_inventory_difference_summary(self.diff_df)
        self.diff_cycle_var.set(
            "Diferencias activas: "
            f"{summary['items']} | +{summary['positive_items']} | -{summary['negative_items']} | neto {summary['net_difference']:+d}"
        )
        archive_dir = get_inventory_difference_archive_dir()
        self.diff_archive_var.set(f"Historial de cierres: {archive_dir}")

    def _has_active_filters(self) -> bool:
        return any(
            [
                bool(self.entry_busqueda.get().strip()),
                bool(self.entry_codigo.get().strip()),
                bool(self.entry_lote_serie.get().strip()),
                self._norm_text(self.subfamilia_var.get()) not in ("", "todas"),
                bool(self.entry_ubicacion_selector.get().strip()),
                bool(self.entry_fila_letra.get().strip()),
                bool(self.entry_posicion.get().strip()),
                bool(self.ubicaciones_seleccionadas),
                self._norm_text(self.bodega_var.get()) not in ("", "todas"),
                bool(self.stock_cero_var.get()),
            ]
        )

    def _abrir_dialogo_diferencia(self):
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        selected = self._selected_view_df()
        if selected.empty:
            self.safe_messagebox("info", "Diferencias", "Selecciona una fila para registrar la diferencia de stock.")
            return
        if len(selected) != 1:
            self.safe_messagebox("info", "Diferencias", "Por ahora registra una diferencia a la vez para asegurar el lote o serie correcto.")
            return

        row = selected.iloc[0]
        current_diff = int(pd.to_numeric(pd.Series([row.get("Dif. Stock", 0)]), errors="coerce").fillna(0).iloc[0])
        current_note = str(row.get("Observación Dif.", "") or "")

        win = tk.Toplevel(self)
        win.title("Registrar diferencia de stock")
        win.geometry("620x460")
        win.minsize(560, 420)
        win.transient(self)
        win.grab_set()
        win.config(bg="#FFFFFF")

        shell = ttk.Frame(win, padding=16)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        ttk.Label(shell, text="Registrar diferencia de stock").grid(row=0, column=0, sticky="w", pady=(0, 8))
        info = "\n".join(
            [
                f"Código: {row.get('Código', '')}",
                f"Producto: {row.get('Producto', '')}",
                f"Ubicación: {row.get('Ubicación', '')}",
                f"Lote: {row.get('Lote', '') or '-'}",
                f"Serie: {row.get('N° Serie', '') or '-'}",
                f"Stock sistema: {row.get('Saldo Stock', 0)}",
            ]
        )
        ttk.Label(shell, text=info, justify="left").grid(row=1, column=0, sticky="we", pady=(0, 12))

        form = ttk.Frame(shell)
        form.grid(row=2, column=0, sticky="nsew")

        ttk.Label(form, text="Diferencia (+/-):").grid(row=0, column=0, sticky="w")
        qty_var = tk.StringVar(value=str(current_diff if current_diff else ""))
        qty_entry = ttk.Entry(form, textvariable=qty_var, width=16)
        qty_entry.grid(row=0, column=1, sticky="w", padx=(8, 0))
        qty_entry.focus_set()

        ttk.Label(form, text="Observación:").grid(row=1, column=0, sticky="nw", pady=(12, 0))
        note_text = tk.Text(form, width=48, height=6, font=("Segoe UI", 10))
        note_text.grid(row=1, column=1, sticky="we", padx=(8, 0), pady=(12, 0))
        if current_note:
            note_text.insert("1.0", current_note)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(1, weight=1)

        def guardar():
            try:
                difference_qty = int(qty_var.get().strip())
            except Exception:
                self.safe_messagebox("error", "Diferencias", "La diferencia debe ser un numero entero, por ejemplo -2 o 5.")
                return

            if difference_qty == 0:
                self.safe_messagebox("info", "Diferencias", "La diferencia no puede ser 0. Usa un valor positivo o negativo.")
                return

            try:
                save_inventory_difference(
                    row,
                    difference_qty=difference_qty,
                    note=note_text.get("1.0", "end").strip(),
                    source_file=self._archivo_actual,
                )
                self._refresh_differences_and_view()
                self.status_var.set(
                    f"Diferencia guardada para {row.get('Código', '')} en {row.get('Ubicación', '')}: {difference_qty:+d}"
                )
                capturar_log_bod1(
                    f"[Inventario] Diferencia guardada para codigo={row.get('Código', '')}, ubicacion={row.get('Ubicación', '')}, lote={row.get('Lote', '')}, serie={row.get('N° Serie', '')}, diferencia={difference_qty}",
                    "info",
                )
                win.destroy()
            except Exception as e:
                capturar_log_bod1(f"[Inventario] Error guardando diferencia: {e}", "error")
                self.safe_messagebox("error", "Diferencias", f"No se pudo guardar la diferencia:\n{e}")

        buttons = ttk.Frame(shell)
        buttons.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="Guardar diferencia", command=guardar).pack(side="right")
        ttk.Button(buttons, text="Cancelar", command=win.destroy).pack(side="right", padx=(0, 8))

    def _abrir_historial_diferencias(self):
        diff_df = get_inventory_differences_df()
        if diff_df.empty:
            self.safe_messagebox("info", "Diferencias", "Todavia no hay diferencias de stock guardadas.")
            return

        win = tk.Toplevel(self)
        win.title("Diferencias guardadas")
        win.geometry("1180x520")
        win.transient(self)
        win.config(bg="#FFFFFF")

        ttk.Label(win, text="Diferencias guardadas").pack(anchor="w", padx=14, pady=(14, 8))

        cols = list(diff_df.columns)
        tree = ttk.Treeview(win, columns=cols, show="headings", height=18)
        for col in cols:
            tree.heading(col, text=col)
            width = 120
            if col == "Producto":
                width = 240
            elif col == "Observación":
                width = 260
            elif col in ("Código", "Bodega", "Ubicación", "Lote", "N° Serie"):
                width = 120
            tree.column(col, width=width, minwidth=80, anchor="center")

        for _, row in diff_df.iterrows():
            tree.insert("", "end", iid=str(row["id"]), values=[row[col] for col in cols])

        tree.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        actions = ttk.Frame(win, padding=(14, 0, 14, 14))
        actions.pack(fill="x")

        def eliminar():
            selected_id = tree.selection()
            if not selected_id:
                self.safe_messagebox("info", "Diferencias", "Selecciona una diferencia para eliminar.")
                return
            record_id = int(selected_id[0])
            try:
                deleted = remove_inventory_difference(record_id)
                if deleted:
                    tree.delete(selected_id[0])
                    self._refresh_differences_and_view()
                    self.status_var.set(f"Diferencia eliminada: id {record_id}")
                else:
                    self.safe_messagebox("warning", "Diferencias", "La diferencia ya no estaba disponible.")
            except Exception as e:
                capturar_log_bod1(f"[Inventario] Error eliminando diferencia: {e}", "error")
                self.safe_messagebox("error", "Diferencias", f"No se pudo eliminar la diferencia:\n{e}")

        ttk.Button(actions, text="Eliminar seleccionada", command=eliminar).pack(side="left")
        ttk.Button(actions, text="Exportar informe", command=self._exportar_informe_diferencias).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Cerrar", command=win.destroy).pack(side="right")

    def _exportar_informe_diferencias(self):
        diff_df = get_inventory_differences_df()
        if diff_df.empty:
            self.safe_messagebox("info", "Informe", "Todavia no hay diferencias de stock guardadas para informar.")
            return

        suggested_name = "informe_diferencias_stock.xlsx"
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar informe de diferencias",
            defaultextension=".xlsx",
            initialdir=str(get_inventory_difference_output_dir()),
            initialfile=suggested_name,
            filetypes=[("Excel", "*.xlsx")],
        )
        if not destination:
            return

        try:
            output_path = export_inventory_difference_report(destination, diff_df=diff_df)
            self.status_var.set(f"Informe de diferencias generado: {output_path.name}")
            capturar_log_bod1(f"[Inventario] Informe de diferencias generado en {output_path}", "info")
            self.safe_messagebox("info", "Informe", f"Informe generado correctamente en:\n{output_path}")
        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error generando informe de diferencias: {e}", "error")
            self.safe_messagebox("error", "Informe", f"No se pudo generar el informe:\n{e}")

    def _cerrar_ciclo_diferencias(self):
        diff_df = get_inventory_differences_df()
        if diff_df.empty:
            self.safe_messagebox("info", "Cierre", "No hay diferencias activas para cerrar.")
            return

        summary = get_inventory_difference_summary(diff_df)
        confirm = messagebox.askyesno(
            "Cerrar ciclo de diferencias",
            "Se archivará el informe actual en la carpeta histórica y se limpiarán las diferencias activas.\n\n"
            f"Registros: {summary['items']}\n"
            f"Diferencia neta: {summary['net_difference']:+d}\n\n"
            "¿Deseas continuar?",
            parent=self,
        )
        if not confirm:
            return

        try:
            archive_path = close_inventory_difference_cycle(diff_df)
            self._refresh_differences_and_view()
            self.status_var.set(f"Ciclo de diferencias cerrado. Archivo histórico: {archive_path.name}")
            capturar_log_bod1(f"[Inventario] Cierre de diferencias generado en {archive_path}", "info")
            self.safe_messagebox(
                "info",
                "Cierre completado",
                f"El informe anterior fue archivado en:\n{archive_path}\n\nSe inició un nuevo ciclo de diferencias.",
            )
        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error cerrando ciclo de diferencias: {e}", "error")
            self.safe_messagebox("error", "Cierre", f"No se pudo cerrar el ciclo de diferencias:\n{e}")

    # ---------------------- Selector de ubicaciones ----------------------

    def _actualizar_label_ubicaciones(self):
        total = len(self.ubicaciones_disponibles)
        sel = len(self.ubicaciones_seleccionadas)
        if sel == 0:
            self.ubicaciones_var.set(f"Ubicaciones: todas ({total})")
            return
        if sel <= 3:
            muestra = ", ".join(sorted(self.ubicaciones_seleccionadas))
            self.ubicaciones_var.set(f"Ubicaciones: {muestra}")
            return
        self.ubicaciones_var.set(f"Ubicaciones seleccionadas: {sel} de {total}")

    def _actualizar_label_ubicaciones_principales(self):
        if not self.ubicaciones_principales_seleccionadas:
            self.ubicaciones_principales_var.set("Ubicaciones: todas")
            return
        ubicaciones = sorted(self.ubicaciones_principales_seleccionadas)
        self.ubicaciones_principales_var.set(f"Ubicaciones: {', '.join(ubicaciones)}")

    def _parse_selector_tokens(self, text: str):
        tokens = []
        for chunk in str(text or "").replace(";", ",").split(","):
            token = self._norm_text(chunk)
            if token:
                tokens.append(token)
        return set(tokens)

    def _split_location_parts(self, ubicacion: str) -> list[str]:
        value = str(ubicacion or "").strip()
        if not value:
            return []
        return [self._norm_text(part) for part in value.split("-") if str(part).strip()]

    def _extract_main_row(self, ubicacion: str) -> str:
        parts = self._split_location_parts(ubicacion)
        return parts[0] if parts else ""

    def _extract_letter_row(self, ubicacion: str) -> str:
        parts = self._split_location_parts(ubicacion)
        if len(parts) < 2:
            return ""
        return self._letters_only(parts[1])

    def _extract_position(self, ubicacion: str) -> str:
        parts = self._split_location_parts(ubicacion)
        if len(parts) >= 3:
            return parts[2]
        if len(parts) == 2:
            return self._digits_only(parts[1])
        return ""

    def _letters_only(self, value: str) -> str:
        return self._norm_text("".join(ch for ch in str(value or "") if ch.isalpha()))

    def _digits_only(self, value: str) -> str:
        return self._norm_text("".join(ch for ch in str(value or "") if ch.isdigit()))

    def _is_location_column(self, column: str) -> bool:
        key = self._norm_text(column)
        return key == "ubicacion" or key.startswith("ubicaci")

    def _location_sort_key(self, ubicacion: str):
        parts = self._split_location_parts(ubicacion)
        if not parts:
            return (1, "", 0, "", 0, "", 0, "")

        main_text, main_number = self._split_location_segment(parts[0])
        row_text, row_number = self._split_location_segment(parts[1] if len(parts) > 1 else "")
        pos_text, pos_number = self._split_location_segment(parts[2] if len(parts) > 2 else "")
        extra = "-".join(parts[3:])

        return (
            0,
            main_text,
            main_number,
            row_text,
            row_number,
            pos_text,
            pos_number,
            extra,
        )

    def _split_location_segment(self, value: str) -> tuple[str, int]:
        value = self._norm_text(value)
        letters = "".join(re.findall(r"[a-z]+", value))
        digits = re.findall(r"\d+", value)
        number = int(digits[0]) if digits else 0
        return letters, number

    def _location_row_matches(self, ubicacion: str, filtro: str) -> bool:
        parts = self._split_location_parts(ubicacion)
        filtro_norm = self._norm_text(filtro)
        if not filtro_norm or len(parts) < 2:
            return False
        row_segment = parts[1]
        return filtro_norm in {row_segment, self._letters_only(row_segment), self._digits_only(row_segment)}

    def _location_position_matches(self, ubicacion: str, filtro: str) -> bool:
        filtro_norm = self._norm_text(filtro)
        if not filtro_norm:
            return False
        position = self._extract_position(ubicacion)
        if not position:
            return False
        return filtro_norm in {position, self._letters_only(position), self._digits_only(position)}

    def _seleccionar_por_ubicacion_principal(self):
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        ubicaciones_principales = self._parse_selector_tokens(self.entry_ubicacion_selector.get())
        if not ubicaciones_principales:
            self.ubicaciones_principales_seleccionadas = set()
            self._actualizar_label_ubicaciones_principales()
            self.status_var.set("Seleccion por ubicacion limpiada.")
            self._filtrar()
            return

        ubicaciones_match = sorted(
            {
                ubicacion
                for ubicacion in self.ubicaciones_disponibles
                if self._extract_main_row(ubicacion) in ubicaciones_principales
            }
        )

        if not ubicaciones_match:
            self.safe_messagebox("info", "Seleccionar ubicación", "No se encontraron ubicaciones para la ubicación indicada.")
            return

        self.ubicaciones_principales_seleccionadas = set(ubicaciones_principales)
        self.ubicaciones_seleccionadas = set(ubicaciones_match)
        self.selected_row_ids = set()
        self._actualizar_label_ubicaciones_principales()
        self._actualizar_label_ubicaciones()

        counts = (
            self.df.assign(__ubicacion_principal=self.df["Ubicación"].map(self._extract_main_row))
            .loc[lambda d: d["__ubicacion_principal"].isin(ubicaciones_principales)]
            .groupby("__ubicacion_principal")
            .size()
            .to_dict()
        )
        resumen = ", ".join(f"{ubicacion}: {counts.get(ubicacion, 0)}" for ubicacion in sorted(ubicaciones_principales))
        self.status_var.set(f"Ubicaciones aplicadas. {resumen}")
        self._filtrar()

    def _abrir_selector_ubicaciones(self):
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        if self._ubic_popup and self._ubic_popup.winfo_exists():
            self._ubic_popup.focus_force()
            return

        popup = tk.Toplevel(self)
        popup.title("Seleccionar ubicaciones")
        popup.geometry("460x520")
        popup.transient(self)
        popup.grab_set()
        popup.config(bg="#FFFFFF")
        self._ubic_popup = popup
        popup.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "_ubic_popup", None), popup.destroy()))

        ttk.Label(popup, text="Buscar ubicación:").pack(anchor="w", padx=12, pady=(12, 4))
        search_var = tk.StringVar(value="")
        entry = ttk.Entry(popup, textvariable=search_var)
        entry.pack(fill="x", padx=12)
        entry.focus_set()

        list_frame = ttk.Frame(popup)
        list_frame.pack(fill="both", expand=True, padx=12, pady=10)

        canvas = tk.Canvas(list_frame, highlightthickness=0, bg="#FFFFFF")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        vars_map = {
            u: tk.BooleanVar(value=(u in self.ubicaciones_seleccionadas))
            for u in self.ubicaciones_disponibles
        }

        def matches_location(location: str, term: str) -> bool:
            if not term:
                return True
            loc_n = self._norm_text(location)
            if term in loc_n:
                return True
            return SequenceMatcher(None, term, loc_n).ratio() >= 0.62

        def on_check_change():
            seleccion = {u for u, var in vars_map.items() if var.get()}
            self.ubicaciones_seleccionadas = seleccion
            self._actualizar_label_ubicaciones()

        def rebuild_list():
            for widget in inner.winfo_children():
                widget.destroy()
            term = self._norm_text(search_var.get())
            visibles = [u for u in self.ubicaciones_disponibles if matches_location(u, term)]
            if not visibles:
                ttk.Label(inner, text="Sin coincidencias").pack(anchor="w", padx=4, pady=4)
                return
            for loc in visibles:
                ttk.Checkbutton(
                    inner,
                    text=loc,
                    variable=vars_map[loc],
                    command=on_check_change,
                ).pack(anchor="w", padx=4, pady=1)

        def seleccionar_visibles(valor: bool):
            term = self._norm_text(search_var.get())
            for loc in self.ubicaciones_disponibles:
                if matches_location(loc, term):
                    vars_map[loc].set(valor)
            on_check_change()
            rebuild_list()

        def aplicar_y_filtrar():
            on_check_change()
            self._filtrar_desde_selector()
            self._ubic_popup = None
            popup.destroy()

        action_row = ttk.Frame(popup)
        action_row.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(action_row, text="Marcar visibles", command=lambda: seleccionar_visibles(True)).pack(side="left")
        ttk.Button(action_row, text="Desmarcar visibles", command=lambda: seleccionar_visibles(False)).pack(side="left", padx=(6, 0))
        ttk.Button(action_row, text="Aplicar", command=aplicar_y_filtrar).pack(side="right")

        search_var.trace_add("write", lambda *_: rebuild_list())
        rebuild_list()

    def _filtrar_desde_selector(self):
        tiene_texto = bool(self._norm_text(self.entry_busqueda.get()))
        tiene_codigo = bool(self._norm_text(self.entry_codigo.get()))
        tiene_lote_serie = bool(self._norm_text(self.entry_lote_serie.get()))
        tiene_subfamilia = self._norm_text(self.subfamilia_var.get()) not in ("", "todas")
        tiene_bodega = self._norm_text(self.bodega_var.get()) not in ("", "todas")
        tiene_stock_cero = bool(self.stock_cero_var.get())
        tiene_fila_letra = bool(self._norm_text(self.entry_fila_letra.get()))
        tiene_posicion = bool(self._norm_text(self.entry_posicion.get()))
        if self.ubicaciones_seleccionadas or tiene_texto or tiene_codigo or tiene_lote_serie or tiene_subfamilia or tiene_bodega or tiene_stock_cero or tiene_fila_letra or tiene_posicion:
            self._filtrar()
        else:
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self.status_var.set("Sin ubicaciones seleccionadas. Mostrando todos los registros.")
            self._actualizar_tree(self.df)

    def _get_inventory_printer_name(self, cfg: dict | None = None) -> str:
        cfg = cfg if isinstance(cfg, dict) else {}
        mode_printers = cfg.get("mode_printers", {})
        if isinstance(mode_printers, dict):
            inventory = mode_printers.get("inventario")
            if isinstance(inventory, str) and inventory.strip():
                return inventory.strip()

        for candidate in (
            cfg.get("report_printer_name"),
            cfg.get("paper_printer_name"),
            cfg.get("default_printer"),
            (cfg.get("paths", {}) or {}).get("default_printer"),
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _actualizar_info_impresora(self, cfg: dict | None = None):
        printer = self._get_inventory_printer_name(cfg)
        if printer:
            self.printer_info_var.set(f"Impresora inventario: {printer}")
        else:
            self.printer_info_var.set("Impresora inventario: predeterminada del sistema")
