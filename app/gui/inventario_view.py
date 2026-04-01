# app/gui/inventario_view.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict

import pandas as pd
import numpy as np

from app.utils.utils import guardar_ultimo_path, load_config
from app.core.logger_eventos import capturar_log_bod1
from app.printer import printer_inventario_codigo, printer_inventario_ubicacion


# Columnas visibles y orden final en la grilla / impresion
VISIBLE_COLUMNS = [
    "Código", "Producto", "Bodega", "Ubicación",
    "N° Serie", "Lote", "Fecha Vencimiento", "Saldo Stock"
]
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

    faltantes = [c for c in VISIBLE_COLUMNS if c not in df2.columns]
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

    mask_any = df2[VISIBLE_COLUMNS].astype(str).apply(lambda s: s.str.strip() != "").any(axis=1)
    df2 = df2.loc[mask_any, VISIBLE_COLUMNS].reset_index(drop=True)

    return df2


class InventarioView(tk.Toplevel):
    PRODUCT_MIN_WIDTH = 280
    PRODUCT_MAX_WIDTH = 620

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventario - Consulta")
        self.geometry("1280x760")
        self.minsize(1080, 640)
        self.config(bg="#EEF2F8")
        try:
            self.transient(parent)
        except Exception:
            pass

        self.df = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.tipo_busqueda = None
        self.sort_column = None
        self.sort_ascending = True
        self.ubicaciones_disponibles = []
        self.ubicaciones_seleccionadas = set()
        self.ubicaciones_principales_seleccionadas = set()
        self.bodegas_disponibles = []
        self.selected_row_ids = set()
        self._ubic_popup = None
        self._archivo_actual = ""
        self.status_var = tk.StringVar(value="Carga un archivo de inventario para comenzar.")
        self.summary_var = tk.StringVar(value="Registros: 0")
        self.ubicaciones_var = tk.StringVar(value="Ubicaciones: todas")
        self.ubicaciones_principales_var = tk.StringVar(value="Ubicaciones: todas")
        self.printer_info_var = tk.StringVar(value="Impresora inventario: sin configurar")
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
        ttk.Label(shell, text="Busqueda por texto, codigo de producto, bodega, ubicacion principal, fila y posicion.", style="InvSub.TLabel").pack(anchor="w", pady=(2, 10))

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

        ttk.Checkbutton(location_block, text="Solo stock 0", variable=self.stock_cero_var, command=self._filtrar).grid(row=0, column=7, padx=(0, 12), sticky="w")
        ttk.Button(location_block, text="Ubicaciones ▼", command=self._abrir_selector_ubicaciones).grid(row=0, column=8, padx=(0, 6), sticky="w")
        location_block.columnconfigure(9, weight=1)

        actions_block = ttk.LabelFrame(filter_shell, text="Acciones", padding=10)
        actions_block.pack(fill="x")
        ttk.Button(actions_block, text="Buscar", command=self._filtrar).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Limpiar", command=self._limpiar_busqueda).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Seleccionar todo", command=self._toggle_select_all).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Abrir Excel", command=self._recargar_archivo).pack(side="left", padx=(0, 8))
        ttk.Button(actions_block, text="Imprimir Resultado", command=self._imprimir_resultado).pack(side="left")

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

            self.df = df
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self.sort_column = None
            self.sort_ascending = True
            self.ubicaciones_disponibles = sorted(df["Ubicación"].dropna().astype(str).str.strip().unique().tolist())
            self.ubicaciones_seleccionadas = set()
            self.ubicaciones_principales_seleccionadas = set()
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
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self.sort_column = None
            self.sort_ascending = True
            self.ubicaciones_disponibles = []
            self.ubicaciones_seleccionadas = set()
            self.ubicaciones_principales_seleccionadas = set()
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

    def _filtrar(self):
        term_raw = self.entry_busqueda.get()
        codigo_producto = self._norm_text(self.entry_codigo.get())
        ubicaciones_principales = self._parse_selector_tokens(self.entry_ubicacion_selector.get())
        self.ubicaciones_principales_seleccionadas = set(ubicaciones_principales)
        self._actualizar_label_ubicaciones_principales()
        bodega = self._norm_text(self.bodega_var.get())
        fila_letra = self._norm_text(self.entry_fila_letra.get())
        posicion = self._norm_text(self.entry_posicion.get())
        solo_stock_cero = bool(self.stock_cero_var.get())

        if not term_raw.strip() and not codigo_producto and not ubicaciones_principales and not fila_letra and not posicion and not self.ubicaciones_seleccionadas and bodega in ("", "todas") and not solo_stock_cero:
            self.safe_messagebox("info", "Buscar", "Ingrese un termino, codigo de producto, ubicacion principal, fila, posicion, bodega, stock 0 o seleccione ubicaciones.")
            return
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        df = self.df.copy()
        terminos = [self._norm_text(t) for t in term_raw.replace(",", " ").split() if t.strip()]

        m_ubi = df["Ubicación"].astype(str).map(self._norm_text)
        m_cod = df["Código"].astype(str).map(self._norm_text)
        m_prod = df["Producto"].astype(str).map(self._norm_text)
        m_bodega = df["Bodega"].astype(str).map(self._norm_text)
        m_ubicacion_principal = df["Ubicación"].astype(str).map(self._extract_main_row)
        m_fila_letra = df["Ubicación"].astype(str).map(self._extract_letter_row)
        m_posicion = df["Ubicación"].astype(str).map(self._extract_position)

        if terminos:
            mask_ubi = m_ubi.apply(lambda val: all(term in val for term in terminos))
            mask_cod = m_cod.apply(lambda val: all(term in val for term in terminos))
            mask_prod = m_prod.apply(lambda val: all(term in val for term in terminos))
            mask_texto = mask_ubi | mask_cod | mask_prod
        else:
            mask_ubi = pd.Series([False] * len(df), index=df.index)
            mask_cod = pd.Series([False] * len(df), index=df.index)
            mask_prod = pd.Series([False] * len(df), index=df.index)
            mask_texto = pd.Series([True] * len(df), index=df.index)

        mask_fila_letra = pd.Series([True] * len(df), index=df.index)
        if fila_letra:
            mask_fila_letra = m_fila_letra == fila_letra

        mask_posicion = pd.Series([True] * len(df), index=df.index)
        if posicion:
            mask_posicion = m_posicion == posicion

        mask_codigo_directo = pd.Series([True] * len(df), index=df.index)
        if codigo_producto:
            mask_codigo_directo = m_cod.apply(lambda val: codigo_producto in val)

        mask_ubicacion_principal = pd.Series([True] * len(df), index=df.index)
        if ubicaciones_principales:
            mask_ubicacion_principal = m_ubicacion_principal.isin(ubicaciones_principales)

        mask_bodega = pd.Series([True] * len(df), index=df.index)
        if bodega and bodega != "todas":
            mask_bodega = m_bodega == bodega

        mask_stock_cero = pd.Series([True] * len(df), index=df.index)
        if solo_stock_cero:
            stock_values = pd.to_numeric(df["Saldo Stock"], errors="coerce").fillna(0)
            mask_stock_cero = stock_values <= 0

        mask_sel_ubic = pd.Series([True] * len(df), index=df.index)
        if self.ubicaciones_seleccionadas:
            sel_norm = {self._norm_text(v) for v in self.ubicaciones_seleccionadas}
            mask_sel_ubic = m_ubi.isin(sel_norm)

        mask_total = mask_texto & mask_codigo_directo & mask_ubicacion_principal & mask_bodega & mask_stock_cero & mask_fila_letra & mask_posicion & mask_sel_ubic

        if mask_total.any():
            self.df_filtrado = df.loc[mask_total].reset_index(drop=True)
            if codigo_producto:
                self.tipo_busqueda = "codigo"
            elif self.ubicaciones_seleccionadas or ubicaciones_principales or bodega not in ("", "todas") or solo_stock_cero or fila_letra or posicion or mask_ubi.any():
                self.tipo_busqueda = "ubicacion"
            elif mask_cod.any():
                self.tipo_busqueda = "codigo"
            elif mask_prod.any():
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
        self.entry_ubicacion_selector.delete(0, "end")
        self.bodega_var.set("Todas")
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

        for i, row in enumerate(df[VISIBLE_COLUMNS].itertuples(index=False)):
            tag = "even" if i % 2 == 0 else "odd"
            marker = "☑" if i in self.selected_row_ids else "☐"
            self.tree.insert("", "end", iid=str(i), values=(marker, *row), tags=(tag,))

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F6F8FD")
        self._autoajustar_columna_producto(df)
        origen = self._archivo_actual or "sin archivo"
        self.summary_var.set(f"Registros: {len(df)} | Fuente: {origen}")

    def _configure_tree_columns(self):
        self.tree.heading("Sel", text="Sel", anchor="center")
        self.tree.column("Sel", width=52, minwidth=52, anchor="center", stretch=False)
        for col in VISIBLE_COLUMNS:
            self.tree.heading(col, text=col, anchor="center", command=lambda c=col: self._sort_by_column(c))
            width = 140
            if col == "Producto":
                width = 280
            elif col in ("Bodega", "Ubicación"):
                width = 160
            elif col in ("Fecha Vencimiento", "Saldo Stock"):
                width = 130
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

    def _selected_view_df(self) -> pd.DataFrame:
        current = self._current_view_df()
        if current is None or current.empty or not self.selected_row_ids:
            return pd.DataFrame()
        valid_indexes = [idx for idx in sorted(self.selected_row_ids) if 0 <= idx < len(current)]
        if not valid_indexes:
            return pd.DataFrame()
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
            idx = int(row_id)
            if idx in self.selected_row_ids:
                self.selected_row_ids.remove(idx)
            else:
                self.selected_row_ids.add(idx)
            self._actualizar_tree(self._current_view_df())
            return "break"

    def _update_heading_texts(self):
        self.tree.heading("Sel", text="Sel", anchor="center")
        for col in VISIBLE_COLUMNS:
            arrow = ""
            if self.sort_column == col:
                arrow = " ▲" if self.sort_ascending else " ▼"
            self.tree.heading(col, text=f"{col}{arrow}", anchor="center", command=lambda c=col: self._sort_by_column(c))

    # ------------------------------ Print -------------------------------

    def _imprimir_resultado(self):
        df_selected = self._selected_view_df()
        df_to_print = df_selected if not df_selected.empty else self._current_view_df()
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
                    config={"printer_name": inventory_printer},
                    df=df_to_print,
                )
            else:
                printer_inventario_codigo.print_inventario_codigo(
                    file_path=self._archivo_actual or "inventario.xlsx",
                    config={"printer_name": inventory_printer},
                    df=df_to_print,
                )

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al imprimir inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo imprimir:\n{e}")

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

    def _extract_main_row(self, ubicacion: str) -> str:
        value = str(ubicacion or "").strip()
        if not value:
            return ""
        main = value.split("-", 1)[0].strip()
        return self._norm_text(main)

    def _extract_letter_row(self, ubicacion: str) -> str:
        value = str(ubicacion or "").strip()
        if "-" not in value:
            return ""
        suffix = value.split("-", 1)[1].strip()
        letters = "".join(ch for ch in suffix if ch.isalpha())
        return self._norm_text(letters)

    def _extract_position(self, ubicacion: str) -> str:
        value = str(ubicacion or "").strip()
        if "-" not in value:
            return ""
        suffix = value.split("-", 1)[1].strip()
        digits = "".join(ch for ch in suffix if ch.isdigit())
        return self._norm_text(digits)

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
        tiene_bodega = self._norm_text(self.bodega_var.get()) not in ("", "todas")
        tiene_stock_cero = bool(self.stock_cero_var.get())
        tiene_col = bool(self._norm_text(self.entry_columna.get()))
        tiene_fila = bool(self._norm_text(self.entry_fila.get()))
        if self.ubicaciones_seleccionadas or tiene_texto or tiene_codigo or tiene_bodega or tiene_stock_cero or tiene_col or tiene_fila:
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
