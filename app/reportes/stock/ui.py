import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from app.db.utils_db import save_file_history
from app.reportes.stock.config import StockReportConfig
from app.reportes.stock.service import StockReportService
from tkcalendar import DateEntry


class StockReportUI:
    """
    GUI para cargar automáticamente el último Informe_stock_fisico_*
    desde una carpeta y aplicar filtros:
      • Vencimiento
      • Stock
      • Criticidad
      • Bodega, Ubicación, Familia, Subfamilia
      • Búsqueda libre
    """

    def __init__(self, parent: tk.Misc, config_json: str = "stock_report_config.json"):
        self.cfg = StockReportConfig.load(Path(config_json))
        self.service = StockReportService(self.cfg)
        self._df = pd.DataFrame()

        self.win = tk.Toplevel(parent)
        self.win.title("Informe de Stock Físico")
        self.win.geometry("1200x700")

        frm = ttk.Frame(self.win, padding=8)
        frm.pack(fill="x")

        # Vencimiento
        ttk.Label(frm, text="Ven Desde:").grid(row=0, column=0)
        self.v1 = DateEntry(frm, date_pattern="yyyy-MM-dd")
        self.v1.set_date(date.today() - timedelta(days=self.cfg.vencimiento_alert_days))
        self.v1.grid(row=0, column=1, padx=4)

        ttk.Label(frm, text="Ven Hasta:").grid(row=0, column=2)
        self.v2 = DateEntry(frm, date_pattern="yyyy-MM-dd")
        self.v2.set_date(date.today() + timedelta(days=self.cfg.vencimiento_alert_days))
        self.v2.grid(row=0, column=3, padx=4)

        # Stock
        ttk.Label(frm, text="Stock:").grid(row=1, column=0)
        self.cb_stock = ttk.Combobox(
            frm,
            values=["Todos", "=0", "<0", ">0 Llegan", ">0 Reserva"],
            width=12,
            state="readonly",
        )
        self.cb_stock.set("Todos")
        self.cb_stock.grid(row=1, column=1, padx=4)

        # Criticidad
        ttk.Label(frm, text="Criticidad:").grid(row=1, column=2)
        crits = ["Todos", "Crítico", "Bajo", "Normal", "Exceso"]
        self.cb_crit = ttk.Combobox(frm, values=crits, width=12, state="readonly")
        self.cb_crit.set("Todos")
        self.cb_crit.grid(row=1, column=3, padx=4)

        # Categóricos
        ttk.Label(frm, text="Bodega:").grid(row=2, column=0)
        self.cb_bod = ttk.Combobox(frm, values=["Todos"], width=15, state="readonly")
        self.cb_bod.grid(row=2, column=1, padx=4)

        ttk.Label(frm, text="Ubicación:").grid(row=2, column=2)
        self.cb_ubic = ttk.Combobox(frm, values=["Todos"], width=15, state="readonly")
        self.cb_ubic.grid(row=2, column=3, padx=4)

        ttk.Label(frm, text="Familia:").grid(row=3, column=0)
        self.cb_fam = ttk.Combobox(frm, values=["Todos"], width=20, state="readonly")
        self.cb_fam.grid(row=3, column=1, padx=4)

        ttk.Label(frm, text="Subfamilia:").grid(row=3, column=2)
        self.cb_sub = ttk.Combobox(frm, values=["Todos"], width=20, state="readonly")
        self.cb_sub.grid(row=3, column=3, padx=4)

        # Búsqueda libre
        ttk.Label(frm, text="Buscar:").grid(row=4, column=0)
        self.search = ttk.Entry(frm, width=30)
        self.search.grid(row=4, column=1, columnspan=3, padx=4)

        # Botones
        ttk.Button(
            frm,
            text="Seleccionar carpeta y cargar último",
            command=self._on_load_folder,
        ).grid(row=5, column=0, pady=12)
        ttk.Button(frm, text="Exportar a Excel", command=self._on_export).grid(
            row=5, column=1, padx=4
        )

        # Treeview
        self.tree = ttk.Treeview(self.win, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

    def _on_load_folder(self):
        folder = filedialog.askdirectory(title="Selecciona carpeta de informes")
        if not folder:
            return
        p = Path(folder)
        files = list(p.glob("Informe_stock_fisico_*.*"))
        if not files:
            messagebox.showerror(
                "Error", "No se encontró ningún Informe_stock_fisico_."
            )
            return
        latest = max(files, key=lambda f: f.stat().st_mtime)

        df = self.service.generate(latest, None, None)
        self._df = df.copy()

        # Rellenar combos
        for cb, col in [
            (self.cb_bod, "Bodega"),
            (self.cb_ubic, "Ubicación"),
            (self.cb_fam, "Familia"),
            (self.cb_sub, "Subfamilia"),
        ]:
            vals = ["Todos"] + sorted(df[col].dropna().unique().tolist())
            cb.config(values=vals)
            cb.set("Todos")

        self._apply_filters()
        try:
            save_file_history(str(latest), modo="stock")
        except:
            pass
        messagebox.showinfo("Cargado", f"Archivo cargado:\n{latest.name}")

    def _apply_filters(self):
        df = self._df.copy()

        # Vencimiento
        mask = (
            pd.to_datetime(df["Fecha Vencimiento"])
            >= pd.to_datetime(self.v1.get_date())
        ) & (
            pd.to_datetime(df["Fecha Vencimiento"])
            <= pd.to_datetime(self.v2.get_date())
        )
        df = df.loc[mask]

        # Stock
        st = self.cb_stock.get()
        if st == "=0":
            df = df[df["Saldo stock"] == 0]
        elif st == "<0":
            df = df[df["Saldo stock"] < 0]
        elif st == ">0 Llegan":
            df = df[df["Por llegar"] > 0]
        elif st == ">0 Reserva":
            df = df[df["Reserva"] > 0]

        # Criticidad
        th, c = self.cfg.thresholds, self.cb_crit.get()
        if c == "Crítico":
            df = df[df["Saldo stock"] < th["critico"]]
        elif c == "Bajo":
            df = df[
                (df["Saldo stock"] >= th["critico"]) & (df["Saldo stock"] < th["bajo"])
            ]
        elif c == "Normal":
            df = df[
                (df["Saldo stock"] >= th["bajo"]) & (df["Saldo stock"] <= th["alto"])
            ]
        elif c == "Exceso":
            df = df[df["Saldo stock"] > th["alto"]]

        # Categóricos
        for cb, col in [
            (self.cb_bod, "Bodega"),
            (self.cb_ubic, "Ubicación"),
            (self.cb_fam, "Familia"),
            (self.cb_sub, "Subfamilia"),
        ]:
            v = cb.get()
            if v != "Todos":
                df = df[df[col] == v]

        # Búsqueda
        key = self.search.get().strip().lower()
        if key:
            m = (
                df["Código"].astype(str).str.lower().str.contains(key)
                | df["Producto"].astype(str).str.lower().str.contains(key)
                | df["Lote"].astype(str).str.lower().str.contains(key)
            )
            df = df.loc[m]

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
        if not self.tree.get_children():
            messagebox.showwarning("Aviso", "No hay datos para exportar.")
            return
        rows = [self.tree.item(i)["values"] for i in self.tree.get_children()]
        df = pd.DataFrame(rows, columns=self.tree["columns"])
        path = filedialog.asksaveasfilename(
            title="Guardar Informe",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            self.service.export(df, Path(path).name)
            messagebox.showinfo("Éxito", f"Exportado a:\n{path}")
