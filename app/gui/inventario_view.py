# app/gui/inventario_view.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import unicodedata
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
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventario - Consulta")
        self.geometry("1280x760")
        self.minsize(1080, 640)
        self.config(bg="#EEF2F8")

        self.df = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.tipo_busqueda = None
        self._archivo_actual = ""
        self.status_var = tk.StringVar(value="Carga un archivo de inventario para comenzar.")
        self.summary_var = tk.StringVar(value="Registros: 0")

        self._crear_widgets()
        self._cargar_o_pedir_archivo()

    # ------------------------------- UI ---------------------------------

    def safe_messagebox(self, tipo, titulo, mensaje):
        self.after(
            0,
            lambda: {
                "info": messagebox.showinfo,
                "error": messagebox.showerror,
                "warning": messagebox.showwarning,
            }[tipo](titulo, mensaje),
        )

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
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))
        style.map("Treeview", background=[("selected", "#C9D8FF")], foreground=[("selected", "#0F1F3D")])

        shell = ttk.Frame(self, style="InvBg.TFrame", padding=14)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="Inventario", style="InvTitle.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Busqueda por codigo, ubicacion, columna y fila.", style="InvSub.TLabel").pack(anchor="w", pady=(2, 10))

        top_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
        top_card.pack(fill="x")

        tk.Label(top_card, text="Buscar:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.entry_busqueda = tk.Entry(top_card, width=34, font=("Segoe UI", 10))
        self.entry_busqueda.grid(row=0, column=1, padx=(6, 12), sticky="w")
        self.entry_busqueda.bind("<Return>", lambda e: self._filtrar())
        self.entry_busqueda.bind("<KeyRelease>", lambda e: self._actualizar_sugerencias())

        tk.Label(top_card, text="Columna:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
        self.entry_columna = tk.Entry(top_card, width=8, font=("Segoe UI", 10))
        self.entry_columna.grid(row=0, column=3, padx=(6, 12), sticky="w")
        self.entry_columna.bind("<Return>", lambda e: self._filtrar())

        tk.Label(top_card, text="Fila:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=4, sticky="w")
        self.entry_fila = tk.Entry(top_card, width=8, font=("Segoe UI", 10))
        self.entry_fila.grid(row=0, column=5, padx=(6, 12), sticky="w")
        self.entry_fila.bind("<Return>", lambda e: self._filtrar())

        ttk.Button(top_card, text="Buscar", command=self._filtrar).grid(row=0, column=6, padx=(0, 6))
        ttk.Button(top_card, text="Limpiar", command=self._limpiar_busqueda).grid(row=0, column=7, padx=(0, 6))
        ttk.Button(top_card, text="Abrir Excel", command=self._recargar_archivo).grid(row=0, column=8, padx=(0, 6))
        ttk.Button(top_card, text="Imprimir Resultado", command=self._imprimir_resultado).grid(row=0, column=9)
        top_card.columnconfigure(10, weight=1)

        info_row = ttk.Frame(top_card, style="Card.TFrame")
        info_row.grid(row=1, column=0, columnspan=11, sticky="ew", pady=(10, 0))
        ttk.Label(info_row, textvariable=self.summary_var, style="InvLabel.TLabel").pack(side="left")
        ttk.Label(info_row, textvariable=self.status_var, style="InvHint.TLabel").pack(side="left", padx=(16, 0))

        self.sugerencias_var = tk.StringVar(value="")
        ttk.Label(shell, textvariable=self.sugerencias_var, style="InvSub.TLabel").pack(anchor="w", padx=2, pady=(8, 4))

        table_card = ttk.Frame(shell, style="Card.TFrame", padding=8)
        table_card.pack(fill="both", expand=True, pady=(0, 8))

        tree_container = ttk.Frame(table_card, style="Card.TFrame")
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_container, columns=VISIBLE_COLUMNS, show="headings", height=25)
        for col in VISIBLE_COLUMNS:
            self.tree.heading(col, text=col)
            width = 140
            if col in ("Producto",):
                width = 280
            elif col in ("Bodega", "Ubicación"):
                width = 160
            elif col in ("Fecha Vencimiento", "Saldo Stock"):
                width = 130
            self.tree.column(col, width=width, anchor="center")

        yscroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

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
        ruta = config.get("archivo_inventario")
        if ruta and Path(ruta).exists():
            self._leer_excel(Path(ruta))
        else:
            self._buscar_y_cargar_archivo()

    def _recargar_archivo(self):
        self._buscar_y_cargar_archivo()

    def _buscar_y_cargar_archivo(self):
        ruta_archivo = filedialog.askopenfilename(
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
            self._archivo_actual = path.name
            self._actualizar_tree(self.df)
            self.status_var.set(f"Archivo cargado: {path.name}")
            self.entry_busqueda.focus_set()

            capturar_log_bod1(f"[Inventario] Archivo cargado: {path}", "info")
            self.safe_messagebox("info", "Inventario", f"Archivo cargado correctamente: {path.name}")

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al cargar inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo cargar el archivo:\n{e}")
            self.df = pd.DataFrame()
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
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
        termino = self._norm_text(term_raw)
        columna = self._norm_text(self.entry_columna.get())
        fila = self._norm_text(self.entry_fila.get())

        if not termino and not columna and not fila:
            self.safe_messagebox("info", "Buscar", "Ingrese un termino, columna o fila para filtrar.")
            return
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        df = self.df.copy()
        terminos = [self._norm_text(t) for t in term_raw.replace(",", " ").split() if t.strip()]

        m_ubi = df["Ubicación"].astype(str).map(self._norm_text)
        m_cod = df["Código"].astype(str).map(self._norm_text)
        m_prod = df["Producto"].astype(str).map(self._norm_text)

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

        mask_col = pd.Series([True] * len(df), index=df.index)
        if columna:
            token_col = columna.lower()
            mask_col = m_ubi.apply(
                lambda val: (
                    f"-{token_col}" in val
                    or f" {token_col}" in val
                    or val.startswith(token_col)
                )
            )

        mask_fila = pd.Series([True] * len(df), index=df.index)
        if fila:
            token_fila = fila.strip()
            mask_fila = m_ubi.apply(
                lambda val: any(token_fila == frag[-1] for frag in val.split("-") if frag and frag[-1].isdigit())
            )

        mask_total = mask_texto & mask_col & mask_fila

        if mask_total.any():
            self.df_filtrado = df.loc[mask_total].reset_index(drop=True)
            if columna or fila or mask_ubi.any():
                self.tipo_busqueda = "ubicacion"
            elif mask_cod.any():
                self.tipo_busqueda = "codigo"
            elif mask_prod.any():
                self.tipo_busqueda = "producto"
            else:
                self.tipo_busqueda = None
            self.status_var.set(f"Filtro aplicado. Resultados: {len(self.df_filtrado)}")
        else:
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self.status_var.set("Sin resultados para el filtro aplicado.")

        self._actualizar_tree(self.df_filtrado)
        self._actualizar_sugerencias()

    def _limpiar_busqueda(self):
        self.entry_busqueda.delete(0, "end")
        self.entry_columna.delete(0, "end")
        self.entry_fila.delete(0, "end")
        self.df_filtrado = pd.DataFrame()
        self.tipo_busqueda = None
        self.sugerencias_var.set("")
        self.status_var.set("Filtros limpiados.")
        self._actualizar_tree(self.df)

    # --------------------------- Actualizar UI ---------------------------

    def _actualizar_tree(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        if df is None or df.empty:
            self.summary_var.set("Registros: 0")
            return

        for i, row in enumerate(df[VISIBLE_COLUMNS].itertuples(index=False)):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=row, tags=(tag,))

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F6F8FD")
        origen = self._archivo_actual or "sin archivo"
        self.summary_var.set(f"Registros: {len(df)} | Fuente: {origen}")

    # ------------------------------ Print -------------------------------

    def _imprimir_resultado(self):
        df_to_print = self.df_filtrado if not self.df_filtrado.empty else self.df
        if df_to_print.empty:
            self.safe_messagebox("warning", "Sin datos", "No hay datos para imprimir.")
            return

        try:
            capturar_log_bod1(
                f"[Inventario] Impresion solicitada (tipo={self.tipo_busqueda or 'completo'}) "
                f"con {len(df_to_print)} registros.",
                "info",
            )

            if self.tipo_busqueda == "ubicacion":
                printer_inventario_ubicacion.print_inventario_ubicacion(df=df_to_print)
            else:
                printer_inventario_codigo.print_inventario_codigo(df=df_to_print)

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al imprimir inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo imprimir:\n{e}")
