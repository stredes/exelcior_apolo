# app/gui/informes_stock.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from pathlib import Path
import pandas as pd

from app.reportes.stock.config import StockReportConfig
from app.reportes.stock.service import StockReportService
from app.db.utils_db import save_file_history
from app.core.logger_bod1 import capturar_log_bod1

def crear_ventana_informes_stock(root=None, config_json="stock_report_config.json"):
    # --- Inicializar ventana ---
    if root is None:
        root = tk._default_root or tk.Tk()
    win = tk.Toplevel(root)
    win.title("Informes de Stock Físico")
    win.geometry("1000x700")

    # --- Cargar configuración y servicio ---
    cfg = StockReportConfig.load(Path(config_json))
    service = StockReportService(cfg)
    df_original = None

    # --- Frame de controles ---
    frm = ttk.Frame(win, padding=10)
    frm.pack(fill="x")

    ttk.Label(frm, text="Inv Desde:").grid(row=0, column=0)
    d1 = DateEntry(frm, date_pattern="yyyy-MM-dd")
    d1.set_date(pd.to_datetime("1900-01-01"))
    d1.grid(row=0, column=1, padx=5)

    ttk.Label(frm, text="Inv Hasta:").grid(row=0, column=2)
    d2 = DateEntry(frm, date_pattern="yyyy-MM-dd")
    d2.set_date(pd.to_datetime("2100-01-01"))
    d2.grid(row=0, column=3, padx=5)

    ttk.Label(frm, text="Ven Desde:").grid(row=0, column=4, padx=(20,0))
    v1 = DateEntry(frm, date_pattern="yyyy-MM-dd")
    v1.set_date(pd.to_datetime("1900-01-01"))
    v1.grid(row=0, column=5, padx=5)

    ttk.Label(frm, text="Ven Hasta:").grid(row=0, column=6)
    v2 = DateEntry(frm, date_pattern="yyyy-MM-dd")
    v2.set_date(pd.to_datetime("2100-01-01"))
    v2.grid(row=0, column=7, padx=5)

    btn_carga = ttk.Button(frm, text="Seleccionar Carpeta → Cargar Último",
                           command=lambda: _cargar_ultimo())
    btn_carga.grid(row=1, column=0, pady=10, sticky="w")

    btn_export = ttk.Button(frm, text="Exportar Filtrado",
                            command=lambda: _exportar())
    btn_export.grid(row=1, column=1, pady=10, sticky="w")

    # --- Treeview ---
    tree = None
    cols = []

    def _mostrar_dataframe(df: pd.DataFrame):
        nonlocal tree, cols
        if tree:
            tree.destroy()
        cols = list(df.columns)
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")
        for _, row in df.iterrows():
            tree.insert("", "end", values=list(row))
        tree.pack(fill="both", expand=True, padx=10, pady=5)

    def _cargar_ultimo():
        nonlocal df_original
        carpeta = filedialog.askdirectory(title="Selecciona carpeta con informes")
        if not carpeta:
            return
        p = Path(carpeta)
        archivos = list(p.glob("Informe_stock_fisico_*.*"))
        if not archivos:
            messagebox.showerror("Error", "No se encontraron archivos coincidentes.")
            return
        ultimo = max(archivos, key=lambda f: f.stat().st_mtime)
        try:
            capturar_log_bod1(f"Cargando último informe: {ultimo}", "info")
            df = service.generate(ultimo, None, None)
            df_original = df.copy()
            save_file_history(str(ultimo), modo="listados")
            _filtrar_mostrar()
            messagebox.showinfo("Cargado", f"Archivo cargado:\n{ultimo.name}")
        except Exception as e:
            capturar_log_bod1(f"Error al cargar informe: {e}", "error")
            messagebox.showerror("Error", f"No se pudo cargar:\n{e}")

    def _filtrar_mostrar():
        if df_original is None:
            return
        df = df_original.copy()
        # Filtro inventario si existe date_field
        if cfg.date_field and cfg.date_field in df.columns:
            df[cfg.date_field] = pd.to_datetime(df[cfg.date_field], dayfirst=True, errors="coerce")
            desde = pd.to_datetime(d1.get_date())
            hasta = pd.to_datetime(d2.get_date())
            df = df[(df[cfg.date_field] >= desde) & (df[cfg.date_field] <= hasta)]
        # Filtro vencimiento
        if "Fecha Vencimiento" in df.columns:
            df["Fecha Vencimiento"] = pd.to_datetime(df["Fecha Vencimiento"], format="%d/%m/%Y", errors="coerce")
            vd = pd.to_datetime(v1.get_date())
            vh = pd.to_datetime(v2.get_date())
            df = df[(df["Fecha Vencimiento"] >= vd) & (df["Fecha Vencimiento"] <= vh)]
        _mostrar_dataframe(df)

    def _exportar():
        if not cols:
            messagebox.showwarning("Aviso", "No hay datos para exportar.")
            return
        rows = [tree.item(i)["values"] for i in tree.get_children()]
        df = pd.DataFrame(rows, columns=cols)
        destino = filedialog.asksaveasfilename(title="Guardar informe",
                                               defaultextension=".xlsx",
                                               filetypes=[("Excel","*.xlsx")])
        if not destino:
            return
        try:
            df.to_excel(destino, index=False)
            capturar_log_bod1(f"Informe exportado: {destino}", "info")
            messagebox.showinfo("Éxito", f"Exportado a:\n{destino}")
        except Exception as e:
            capturar_log_bod1(f"Error exportando informe: {e}", "error")
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    # Modal
    win.transient(root)
    win.grab_set()
    win.wait_window()
