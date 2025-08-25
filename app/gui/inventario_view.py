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


# Columnas visibles y orden final en la grilla / impresión
VISIBLE_COLUMNS = [
    "Código", "Producto", "Bodega", "Ubicación",
    "N° Serie", "Lote", "Fecha Vencimiento", "Saldo Stock"
]

# Sinónimos (normalizados a minúsculas y sin acentos) -> nombre objetivo
COL_SYNONYMS: Dict[str, str] = {
    # Código
    "codigo": "Código",
    "código": "Código",

    # Producto
    "producto": "Producto",
    "descripcion": "Producto",
    "descripción": "Producto",

    # Bodega
    "bodega": "Bodega",

    # Ubicación
    "ubicacion": "Ubicación",
    "ubicación": "Ubicación",

    # N° Serie
    "n serie": "N° Serie",
    "n° serie": "N° Serie",
    "numero serie": "N° Serie",
    "número serie": "N° Serie",
    "num serie": "N° Serie",

    # Lote
    "lote": "Lote",

    # Fecha Vencimiento
    "fecha vencimiento": "Fecha Vencimiento",
    "fec venc": "Fecha Vencimiento",
    "vencimiento": "Fecha Vencimiento",

    # Saldo Stock
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

    # Si hay variantes con espacios/acentos mínimos que no mapeamos, intenta heurística
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
    """Limpia tipos/NaN para UI y posterior impresión."""
    df2 = df.copy()

    # Asegurar columnas visibles
    faltantes = [c for c in VISIBLE_COLUMNS if c not in df2.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {faltantes}")

    # Texto seguro
    for c in ["Código", "Producto", "Bodega", "Ubicación", "N° Serie", "Lote"]:
        df2[c] = df2[c].astype(str).replace({"nan": "", "<NA>": ""}).fillna("").str.strip()

    # Fecha a texto legible (no forzamos dtype datetime aquí para no romper UI)
    if "Fecha Vencimiento" in df2.columns:
        # Intenta parsear; si no, deja tal cual
        dt = pd.to_datetime(df2["Fecha Vencimiento"], errors="coerce", dayfirst=True)
        df2["Fecha Vencimiento"] = np.where(
            dt.notna(),
            dt.dt.strftime("%d/%m/%Y"),
            df2["Fecha Vencimiento"].astype(str).replace({"nan": ""}).fillna("")
        )

    # Saldo Stock como entero >= 0
    df2["Saldo Stock"] = pd.to_numeric(df2["Saldo Stock"], errors="coerce").fillna(0).astype(int)

    # Elimina filas totalmente vacías (en texto) y reordena columnas
    mask_any = df2[VISIBLE_COLUMNS].astype(str).apply(lambda s: s.str.strip() != "").any(axis=1)
    df2 = df2.loc[mask_any, VISIBLE_COLUMNS].reset_index(drop=True)

    return df2


class InventarioView(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventario - Consulta")
        self.geometry("1200x700")
        self.config(bg="#F9FAFB")

        self.df = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.tipo_busqueda = None

        self._crear_widgets()
        self._cargar_o_pedir_archivo()

    # ------------------------------- UI ---------------------------------

    def safe_messagebox(self, tipo, titulo, mensaje):
        self.after(0, lambda: {
            "info": messagebox.showinfo,
            "error": messagebox.showerror,
            "warning": messagebox.showwarning
        }[tipo](titulo, mensaje))

    def _crear_widgets(self):
        top_frame = tk.Frame(self, bg="#F9FAFB")
        top_frame.pack(pady=10, fill="x")

        tk.Label(top_frame, text="Buscar por Código o Ubicación:", bg="#F9FAFB").pack(side="left", padx=(10, 5))
        self.entry_busqueda = tk.Entry(top_frame, width=40)
        self.entry_busqueda.pack(side="left", padx=5)
        self.entry_busqueda.bind("<Return>", lambda e: self._filtrar())

        ttk.Button(top_frame, text="Buscar", command=self._filtrar).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Limpiar", command=self._limpiar_busqueda).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Buscar Archivo Excel", command=self._recargar_archivo).pack(side="left", padx=5)
        ttk.Button(top_frame, text="🖨️ Imprimir Resultado", command=self._imprimir_resultado).pack(side="right", padx=10)

        # Treeview
        self.tree = ttk.Treeview(self, columns=VISIBLE_COLUMNS, show="headings", height=25)
        for col in VISIBLE_COLUMNS:
            self.tree.heading(col, text=col)
            # Ajustes de ancho sugeridos
            width = 140
            if col in ("Producto",):
                width = 280
            elif col in ("Bodega", "Ubicación"):
                width = 160
            elif col in ("Fecha Vencimiento", "Saldo Stock"):
                width = 130
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

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
            filetypes=[("Archivos Excel", "*.xlsx *.xls")]
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
                        "o guarda el archivo como .xlsx e inténtalo nuevamente."
                    )
            else:
                raise ValueError("Extensión de archivo no soportada. Usa .xlsx o .xls")

            df = _normalize_headers(df)
            df = _clean_for_view(df)

            self.df = df
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self._actualizar_tree(self.df)

            capturar_log_bod1(f"[Inventario] Archivo cargado: {path}", "info")
            self.safe_messagebox("info", "Inventario", f"Archivo cargado correctamente: {path.name}")

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al cargar inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo cargar el archivo:\n{e}")
            self.df = pd.DataFrame()
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None
            self._actualizar_tree(self.df)

    # ----------------------------- Búsqueda ------------------------------

    def _norm_text(self, s: str) -> str:
        s = str(s or "").strip().lower()
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return " ".join(s.split())

    def _filtrar(self):
        termino = self._norm_text(self.entry_busqueda.get())
        if not termino:
            self.safe_messagebox("info", "Buscar", "Ingrese un término de búsqueda.")
            return
        if self.df.empty:
            self.safe_messagebox("warning", "Inventario", "Cargue primero un archivo de inventario.")
            return

        df = self.df.copy()
        m_cod = df["Código"].astype(str).map(self._norm_text).str.contains(termino, na=False)
        m_ubi = df["Ubicación"].astype(str).map(self._norm_text).str.contains(termino, na=False)

        if m_cod.any():
            self.df_filtrado = df.loc[m_cod].reset_index(drop=True)
            self.tipo_busqueda = "codigo"
        elif m_ubi.any():
            self.df_filtrado = df.loc[m_ubi].reset_index(drop=True)
            self.tipo_busqueda = "ubicacion"
        else:
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None

        self._actualizar_tree(self.df_filtrado)

    def _limpiar_busqueda(self):
        self.entry_busqueda.delete(0, "end")
        self.df_filtrado = pd.DataFrame()
        self.tipo_busqueda = None
        self._actualizar_tree(self.df)

    # --------------------------- Actualizar UI ---------------------------

    def _actualizar_tree(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        if df is None or df.empty:
            return
        for row in df[VISIBLE_COLUMNS].itertuples(index=False):
            self.tree.insert("", "end", values=row)

    # ------------------------------ Print -------------------------------

    def _imprimir_resultado(self):
        # Usa el filtrado si existe; si no, imprime todo el dataset ya limpio
        df_to_print = self.df_filtrado if not self.df_filtrado.empty else self.df
        if df_to_print.empty:
            self.safe_messagebox("warning", "Sin datos", "No hay datos para imprimir.")
            return

        try:
            capturar_log_bod1(
                f"[Inventario] Impresión solicitada (tipo={self.tipo_busqueda or 'completo'}) "
                f"con {len(df_to_print)} registros.",
                "info"
            )

            # Deriva a la impresora adecuada según el tipo de búsqueda (o por defecto por código)
            if self.tipo_busqueda == "ubicacion":
                printer_inventario_ubicacion.print_inventario_ubicacion(df=df_to_print)
            else:
                printer_inventario_codigo.print_inventario_codigo(df=df_to_print)

        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error al imprimir inventario: {e}", "error")
            self.safe_messagebox("error", "Error", f"No se pudo imprimir:\n{e}")
