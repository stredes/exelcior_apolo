# app/gui/informes_existencia_view.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
import unicodedata
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from app.core.logger_eventos import capturar_log_bod1
from app.services.informes_existencia_service import EXISTENCE_COLUMNS, load_product_movements
from app.utils.utils import guardar_ultimo_path, load_config


class InformesExistenciaView(tk.Toplevel):
    CONFIG_KEY = "archivo_informes_existencia"

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Informes de existencia")
        self.geometry("1320x780")
        self.minsize(1100, 640)
        self.configure(bg="#EEF2F8")
        try:
            self.transient(parent)
        except Exception:
            pass

        self.df = pd.DataFrame(columns=EXISTENCE_COLUMNS)
        self.df_filtrado = pd.DataFrame(columns=EXISTENCE_COLUMNS)
        self._archivo_actual = ""
        self.status_var = tk.StringVar(value="Carga un informe de existencias para ver los movimientos del producto.")
        self.summary_var = tk.StringVar(value="Movimientos: 0 | Entrada: 0 | Salida: 0 | Saldo: 0")
        self.producto_var = tk.StringVar(value="")
        self.codigo_var = tk.StringVar(value="")
        self.serie_var = tk.StringVar(value="")
        self.modalidad_var = tk.StringVar(value="Todas")

        self._crear_widgets()
        self._present_window()
        self._cargar_archivo_guardado()

    def _present_window(self):
        try:
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(300, lambda: self.attributes("-topmost", False))
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
        style.map("Treeview", background=[("selected", "#C9D8FF")], foreground=[("selected", "#0F1F3D")])

        shell = ttk.Frame(self, style="InvBg.TFrame", padding=14)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="Informes de existencia", style="InvTitle.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text="Carga el archivo de existencias y revisa los movimientos por producto, documento, modalidad, serie, entrada, salida y saldo.",
            style="InvSub.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        top_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
        top_card.pack(fill="x")

        filtros = ttk.LabelFrame(top_card, text="Filtros", padding=10)
        filtros.pack(fill="x", pady=(0, 8))

        tk.Label(filtros, text="Producto:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        producto_entry = ttk.Entry(filtros, textvariable=self.producto_var, width=36)
        producto_entry.grid(row=0, column=1, padx=(6, 12), sticky="w")
        producto_entry.bind("<Return>", lambda _e: self._filtrar())

        tk.Label(filtros, text="Código:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
        codigo_entry = ttk.Entry(filtros, textvariable=self.codigo_var, width=18)
        codigo_entry.grid(row=0, column=3, padx=(6, 12), sticky="w")
        codigo_entry.bind("<Return>", lambda _e: self._filtrar())

        tk.Label(filtros, text="N° Serie:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=4, sticky="w")
        serie_entry = ttk.Entry(filtros, textvariable=self.serie_var, width=20)
        serie_entry.grid(row=0, column=5, padx=(6, 12), sticky="w")
        serie_entry.bind("<Return>", lambda _e: self._filtrar())

        tk.Label(filtros, text="Modalidad:", bg="#FFFFFF", fg="#263754", font=("Segoe UI", 10)).grid(row=0, column=6, sticky="w")
        self.combo_modalidad = ttk.Combobox(filtros, textvariable=self.modalidad_var, state="readonly", width=22)
        self.combo_modalidad.grid(row=0, column=7, padx=(6, 0), sticky="w")
        self.combo_modalidad["values"] = ["Todas"]
        self.combo_modalidad.current(0)
        self.combo_modalidad.bind("<<ComboboxSelected>>", lambda _e: self._filtrar())
        filtros.columnconfigure(8, weight=1)

        acciones = ttk.LabelFrame(top_card, text="Acciones", padding=10)
        acciones.pack(fill="x")
        ttk.Button(acciones, text="Cargar archivo", command=self._seleccionar_archivo).pack(side="left", padx=(0, 8))
        ttk.Button(acciones, text="Buscar", command=self._filtrar).pack(side="left", padx=(0, 8))
        ttk.Button(acciones, text="Limpiar filtros", command=self._limpiar_filtros).pack(side="left")

        info_row = ttk.Frame(top_card, style="Card.TFrame")
        info_row.pack(fill="x", pady=(12, 0))
        ttk.Label(info_row, textvariable=self.summary_var, style="InvLabel.TLabel").pack(side="left")
        ttk.Label(info_row, textvariable=self.status_var, style="InvHint.TLabel").pack(side="left", padx=(16, 0))

        table_card = ttk.Frame(shell, style="Card.TFrame", padding=8)
        table_card.pack(fill="both", expand=True, pady=(10, 8))

        tree_frame = ttk.Frame(table_card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=EXISTENCE_COLUMNS, show="headings", height=24)
        self._configure_tree()
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        ttk.Label(shell, textvariable=self.summary_var, style="InvStatus.TLabel").pack(fill="x")

    def _configure_tree(self):
        widths = {
            "Código": 120,
            "Producto": 340,
            "Fecha": 110,
            "Documento": 140,
            "Modalidad": 140,
            "Unidad de stock": 110,
            "Bodega": 140,
            "Ubicación": 140,
            "Cantidad": 100,
            "N° Serie": 140,
            "Entrada": 100,
            "Salida": 100,
            "Saldo": 100,
        }
        for col in EXISTENCE_COLUMNS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths.get(col, 120), minwidth=90, anchor="center", stretch=True)

    def _safe_messagebox(self, tipo: str, titulo: str, mensaje: str):
        mapping = {
            "info": messagebox.showinfo,
            "warning": messagebox.showwarning,
            "error": messagebox.showerror,
        }
        fn = mapping.get(tipo, messagebox.showinfo)
        self.after(0, lambda: fn(titulo, mensaje, parent=self))

    def _norm_text(self, value) -> str:
        text = "" if value is None else str(value)
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        return " ".join(text.strip().lower().split())

    def _cargar_archivo_guardado(self):
        config = load_config() or {}
        ruta = config.get(self.CONFIG_KEY)
        if ruta and Path(ruta).exists():
            self._cargar_dataframe(Path(ruta), notify=False)

    def _seleccionar_archivo(self):
        ruta = filedialog.askopenfilename(
            parent=self,
            title="Selecciona el informe de existencias",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")],
        )
        if not ruta:
            return
        guardar_ultimo_path(ruta, clave=self.CONFIG_KEY)
        self._cargar_dataframe(Path(ruta), notify=True)

    def _cargar_dataframe(self, path: Path, notify: bool):
        try:
            df = load_product_movements(path)
            self.df = df
            self.df_filtrado = pd.DataFrame(columns=EXISTENCE_COLUMNS)
            self._archivo_actual = path.name
            self._refresh_modalidades()
            self._actualizar_tree(self.df)
            self.status_var.set(f"Archivo cargado: {path.name}")
            capturar_log_bod1(f"[Informes de existencia] Archivo cargado: {path}", "info")
            if notify:
                self._safe_messagebox("info", "Informes de existencia", f"Archivo cargado correctamente: {path.name}")
        except Exception as exc:
            self.df = pd.DataFrame(columns=EXISTENCE_COLUMNS)
            self.df_filtrado = pd.DataFrame(columns=EXISTENCE_COLUMNS)
            self._archivo_actual = ""
            self._refresh_modalidades()
            self._actualizar_tree(self.df)
            self.status_var.set("No se pudo cargar el archivo.")
            capturar_log_bod1(f"[Informes de existencia] Error al cargar archivo: {exc}", "error")
            self._safe_messagebox("error", "Informes de existencia", f"No se pudo cargar el archivo:\n{exc}")

    def _refresh_modalidades(self):
        if self.df.empty or "Modalidad" not in self.df.columns:
            self.combo_modalidad["values"] = ["Todas"]
            self.modalidad_var.set("Todas")
            return
        modalidades = sorted(
            {
                str(value).strip()
                for value in self.df["Modalidad"].dropna().tolist()
                if str(value).strip()
            }
        )
        self.combo_modalidad["values"] = ["Todas"] + modalidades
        if self.modalidad_var.get() not in self.combo_modalidad["values"]:
            self.modalidad_var.set("Todas")

    def _filtrar(self):
        if self.df.empty:
            self._safe_messagebox("warning", "Informes de existencia", "Primero carga un informe de existencias.")
            return

        producto = self._norm_text(self.producto_var.get())
        codigo = self._norm_text(self.codigo_var.get())
        serie = self._norm_text(self.serie_var.get())
        modalidad = self._norm_text(self.modalidad_var.get())

        df = self.df.copy()
        if producto:
            df = df[df["Producto"].map(self._norm_text).str.contains(producto, na=False)]
        if codigo:
            df = df[df["Código"].map(self._norm_text).str.contains(codigo, na=False)]
        if serie:
            df = df[df["N° Serie"].map(self._norm_text).str.contains(serie, na=False)]
        if modalidad and modalidad != "todas":
            df = df[df["Modalidad"].map(self._norm_text) == modalidad]

        self.df_filtrado = df.reset_index(drop=True)
        if self.df_filtrado.empty:
            self.status_var.set("Sin movimientos para los filtros aplicados.")
        else:
            self.status_var.set(f"Filtro aplicado. Movimientos visibles: {len(self.df_filtrado)}")
        self._actualizar_tree(self.df_filtrado)

    def _limpiar_filtros(self):
        self.producto_var.set("")
        self.codigo_var.set("")
        self.serie_var.set("")
        self.modalidad_var.set("Todas")
        self.df_filtrado = pd.DataFrame(columns=EXISTENCE_COLUMNS)
        self.status_var.set("Filtros limpiados.")
        self._actualizar_tree(self.df)

    def _actualizar_tree(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        if df is None or df.empty:
            self.summary_var.set("Movimientos: 0 | Entrada: 0 | Salida: 0 | Saldo: 0")
            return

        for idx, row in enumerate(df[EXISTENCE_COLUMNS].itertuples(index=False)):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=row, tags=(tag,))
        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F6F8FD")
        self._autoajustar_producto(df)
        entrada = int(pd.to_numeric(df["Entrada"], errors="coerce").fillna(0).sum())
        salida = int(pd.to_numeric(df["Salida"], errors="coerce").fillna(0).sum())
        saldo = int(pd.to_numeric(df["Saldo"], errors="coerce").fillna(0).sum())
        origen = self._archivo_actual or "sin archivo"
        self.summary_var.set(
            f"Movimientos: {len(df)} | Entrada: {entrada} | Salida: {salida} | Saldo: {saldo} | Fuente: {origen}"
        )

    def _autoajustar_producto(self, df: pd.DataFrame):
        try:
            font = tkfont.nametofont(str(self.tree.cget("font")))
        except Exception:
            font = tkfont.Font(family="Segoe UI", size=10)

        width_px = font.measure("Producto") + 36
        for value in df["Producto"].astype(str).fillna("").head(250):
            width_px = max(width_px, font.measure(value) + 36)
        width_px = max(280, min(width_px, 700))
        self.tree.column("Producto", width=width_px)
