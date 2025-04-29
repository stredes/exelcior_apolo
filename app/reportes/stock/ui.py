# app/reportes/stock/ui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from pathlib import Path
import pandas as pd
from datetime import date, timedelta

from app.reportes.stock.config import StockReportConfig
from app.reportes.stock.service import StockReportService
from app.db.utils_db import save_file_history


class StockReportUI:
    """
    Interfaz para filtrar y visualizar inventario físico con:
      • Fecha inventario (rango)
      • Fecha de vencimiento (rango)
      • SKU / Descripción / Lote (busqueda libre)
      • Bodega
      • Ubicación exacta
      • Familia / Categoría
      • Nivel de stock (cero, por llegar, reserva)
      • Criticidad (según thresholds)
      • Estado de calidad (caducado, por vencer pronto)
      • Usuario snapshot (si aplica)
    """

    def __init__(self, parent: tk.Misc, config_json: str = "stock_report_config.json"):
        # Carga config y servicio
        cfg_path = Path(config_json)
        self.cfg = StockReportConfig.load(cfg_path)
        self.service = StockReportService(self.cfg)

        # Ventana
        self.win = tk.Toplevel(parent)
        self.win.title("Informe de Stock Físico")
        self.win.geometry("1200x700")

        # --- FRAME CONTROLES FILTROS ---
        frm = ttk.Frame(self.win, padding=10)
        frm.pack(fill="x", padx=5, pady=5)

        # Fecha inventario
        ttk.Label(frm, text="Fecha Inventario Desde:").grid(row=0, column=0, sticky="w")
        self.d1 = DateEntry(frm, date_pattern="yyyy-MM-dd")
        self.d1.set_date(date.today() - timedelta(days=30))
        self.d1.grid(row=0, column=1, padx=5)

        ttk.Label(frm, text="Hasta:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.d2 = DateEntry(frm, date_pattern="yyyy-MM-dd")
        self.d2.set_date(date.today())
        self.d2.grid(row=0, column=3, padx=5)

        # Fecha de vencimiento
        ttk.Label(frm, text="Vencimiento Desde:").grid(row=1, column=0, sticky="w", pady=(10,0))
        self.v1 = DateEntry(frm, date_pattern="yyyy-MM-dd")
        self.v1.grid(row=1, column=1, padx=5, pady=(10,0))

        ttk.Label(frm, text="Hasta:").grid(row=1, column=2, sticky="w", padx=(10,0), pady=(10,0))
        self.v2 = DateEntry(frm, date_pattern="yyyy-MM-dd")
        self.v2.grid(row=1, column=3, padx=5, pady=(10,0))

        # Búsqueda libre (SKU, Descripción, Lote)
        ttk.Label(frm, text="Buscar (SKU/Desc/Lote):").grid(row=0, column=4, sticky="w", padx=(20,0))
        self.e_search = ttk.Entry(frm, width=25)
        self.e_search.grid(row=0, column=5, padx=5, pady=2, columnspan=2)

        # Bodega
        ttk.Label(frm, text="Bodega:").grid(row=1, column=4, sticky="w", padx=(20,0))
        self.cb_bodega = ttk.Combobox(frm, values=["Todos"], state="readonly", width=15)
        self.cb_bodega.current(0)
        self.cb_bodega.grid(row=1, column=5, padx=5, pady=(10,0))

        # Ubicación exacta
        ttk.Label(frm, text="Ubicación:").grid(row=1, column=6, sticky="w", padx=(10,0), pady=(10,0))
        self.cb_ubic = ttk.Combobox(frm, values=["Todos"], state="readonly", width=15)
        self.cb_ubic.current(0)
        self.cb_ubic.grid(row=1, column=7, padx=5, pady=(10,0))

        # Familia / Categoría
        ttk.Label(frm, text="Familia:").grid(row=2, column=0, sticky="w", pady=(10,0))
        self.cb_familia = ttk.Combobox(frm, values=["Todos"], state="readonly", width=20)
        self.cb_familia.current(0)
        self.cb_familia.grid(row=2, column=1, padx=5, pady=(10,0), columnspan=2)

        # Nivel de stock
        ttk.Label(frm, text="Nivel Stock:").grid(row=2, column=3, sticky="w", pady=(10,0))
        self.cb_nivel = ttk.Combobox(
            frm, values=["Todos", "Stock 0", "Por llegar", "Reserva"], state="readonly", width=15
        )
        self.cb_nivel.current(0)
        self.cb_nivel.grid(row=2, column=4, padx=5, pady=(10,0))

        # Criticidad
        ttk.Label(frm, text="Criticidad:").grid(row=2, column=5, sticky="w", pady=(10,0))
        crits = ["Todos", "Crítico", "Bajo", "Normal", "Exceso"]
        self.cb_crit = ttk.Combobox(frm, values=crits, state="readonly", width=15)
        self.cb_crit.current(0)
        self.cb_crit.grid(row=2, column=6, padx=5, pady=(10,0))

        # Estado de caducidad
        ttk.Label(frm, text="Caducidad:").grid(row=2, column=7, sticky="w", pady=(10,0))
        self.cb_cadu = ttk.Combobox(
            frm, values=["Todos", "Caducado", "Por vencer pronto"], state="readonly", width=15
        )
        self.cb_cadu.current(0)
        self.cb_cadu.grid(row=2, column=8, padx=5, pady=(10,0))

        # Botones
        btn_load = ttk.Button(frm, text="Cargar Inventario", command=self._on_load)
        btn_load.grid(row=3, column=0, pady=15)
        btn_appf = ttk.Button(frm, text="Aplicar Filtros", command=self._on_apply)
        btn_appf.grid(row=3, column=1, pady=15, padx=5)
        btn_export = ttk.Button(frm, text="Exportar", command=self._on_export)
        btn_export.grid(row=3, column=2, pady=15, padx=5)

        # --- TREEVIEW ---
        self.tree = ttk.Treeview(self.win, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # DataFrame en memoria
        self._df_master = pd.DataFrame()

    def _on_load(self):
        path = filedialog.askopenfilename(
            title="Seleccionar stock físico",
            filetypes=[("Excel","*.xls *.xlsx"),("CSV","*.csv")]
        )
        if not path:
            return
        df = self.service.generate(
            Path(path),
            pd.to_datetime(self.d1.get_date()),
            pd.to_datetime(self.d2.get_date())
        )
        self._df_master = df.copy()

        # rellenar valores únicos en comboboxes
        self.cb_bodega.config(values=["Todos"] + sorted(df["Bodega"].dropna().unique()))
        self.cb_ubic .config(values=["Todos"] + sorted(df["Ubicación"].dropna().unique()))
        self.cb_familia.config(values=["Todos"] + sorted(df["Familia"].dropna().unique()))

        self._populate(df)
        try: save_file_history(path, modo="stock")
        except: pass

    def _on_apply(self):
        df = self._df_master.copy()
        # Bodega
        val = self.cb_bodega.get()
        if val != "Todos": df = df[df["Bodega"] == val]
        # Ubicación
        val = self.cb_ubic.get()
        if val != "Todos": df = df[df["Ubicación"] == val]
        # Familia
        val = self.cb_familia.get()
        if val != "Todos": df = df[df["Familia"] == val]
        # Nivel Stock
        lvl = self.cb_nivel.get()
        if lvl == "Stock 0": df = df[df["saldo_stock"] == 0]
        elif lvl == "Por llegar": df = df[df["por_llegar"] > 0]
        elif lvl == "Reserva": df = df[df["reserva"] > 0]
        # Criticidad
        crit = self.cb_crit.get()
        th = self.cfg.thresholds
        if crit == "Crítico": df = df[df["Cantidad"] < th["critico"]]
        elif crit == "Bajo":    df = df[(df["Cantidad"] >= th["critico"]) & (df["Cantidad"] < th["bajo"])]
        elif crit == "Normal":  df = df[(df["Cantidad"] >= th["bajo"])   & (df["Cantidad"] <= th["alto"])]
        elif crit == "Exceso":  df = df[df["Cantidad"] > th["alto"]]
        # Caducidad
        cad = self.cb_cadu.get()
        hoy = pd.to_datetime(date.today())
        if cad == "Caducado": df = df[pd.to_datetime(df["fecha_vencimiento"]) < hoy]
        elif cad == "Por vencer pronto":
            prox = hoy + pd.Timedelta(days=7)
            df = df[(pd.to_datetime(df["fecha_vencimiento"]) >= hoy) & (pd.to_datetime(df["fecha_vencimiento"]) <= prox)]
        # Búsqueda libre
        key = self.e_search.get().strip().lower()
        if key:
            mask = (
                df["SKU"].astype(str).str.lower().str.contains(key) |
                df["Descripción"].astype(str).str.lower().str.contains(key) |
                df["Lote"].astype(str).str.lower().str.contains(key)
            )
            df = df[mask]

        self._populate(df)

    def _populate(self, df: pd.DataFrame):
        cols = list(df.columns)
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=list(row))

    def _on_export(self):
        if self.tree.get_children()==():
            messagebox.showwarning("Aviso","No hay datos para exportar.")
            return
        rows = [self.tree.item(i)["values"] for i in self.tree.get_children()]
        df = pd.DataFrame(rows, columns=self.tree["columns"])
        save = filedialog.asksaveasfilename(
            title="Guardar Informe",
            defaultextension=".xlsx",
            filetypes=[("Excel","*.xlsx")]
        )
        if not save: return
        try:
            self.service.export(df, Path(save).name)
            messagebox.showinfo("Éxito",f"Exportado a:\n{save}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
