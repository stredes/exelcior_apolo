import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime
from pathlib import Path
from app.printer.printer import print_document
from app.core.logger_bod1 import capturar_log_bod1

class ConsultaCodigoApp(tk.Toplevel):
    COLUMNAS = ["Código", "Producto", "Bodega", "Ubicación", "Lote", "Fecha Vencimiento", "Saldo stock"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Consulta por Código")
        self.geometry("1100x600")
        self.configure(bg="#e6e9e7")

        tk.Label(self, text="Consulta por Código", font=("Segoe UI", 18, "bold", "italic"),
                 fg="red", bg="#e6e9e7").pack(pady=10)

        filtro_frame = tk.Frame(self, bg="#e6e9e7")
        filtro_frame.pack(pady=5)

        tk.Label(filtro_frame, text="Código:", font=("Segoe UI", 10, "bold"),
                 fg="red", bg="#e6e9e7").grid(row=0, column=0)
        self.codigo_entry = ttk.Entry(filtro_frame, width=20)
        self.codigo_entry.grid(row=0, column=1, padx=5)

        ttk.Button(filtro_frame, text="Buscar", command=self.buscar).grid(row=0, column=2, padx=5)

        tk.Label(filtro_frame, text="Entregado a:", font=("Segoe UI", 10, "bold"),
                 fg="red", bg="#e6e9e7").grid(row=0, column=3, padx=(30, 5))
        self.entregado_entry = ttk.Entry(filtro_frame, width=30)
        self.entregado_entry.grid(row=0, column=4)

        self.tree = ttk.Treeview(self, columns=self.COLUMNAS, show="headings")
        for col in self.COLUMNAS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor=tk.CENTER)
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        self.total_label = tk.Label(self, text="Total Stock: 0", font=("Segoe UI", 12, "bold"),
                                    fg="red", bg="#e6e9e7")
        self.total_label.pack(pady=5)

        ttk.Button(self, text="Imprimir", command=self.imprimir).pack(pady=5)

        self.df = self._cargar_excel_reciente()

    def _cargar_excel_reciente(self):
        path = Path.home() / "Downloads"
        archivos = sorted(path.glob("Informe_stock_fisico_*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not archivos:
            messagebox.showerror("Error", "No se encontró ningún archivo de stock físico.")
            self.destroy()
            return pd.DataFrame()
        return pd.read_excel(archivos[0])

    def buscar(self):
        codigo = self.codigo_entry.get().strip()
        if not codigo or self.df.empty:
            return
        self.df_filtrado = self.df[self.df["Código"].astype(str) == codigo]
        self.tree.delete(*self.tree.get_children())
        for _, row in self.df_filtrado.iterrows():
            self.tree.insert("", "end", values=[row.get(col, "") for col in self.COLUMNAS])
        self.total_label.config(text=f"Total Stock: {self.df_filtrado['Saldo stock'].sum()}")

    def imprimir(self):
        if not hasattr(self, "df_filtrado") or self.df_filtrado.empty:
            messagebox.showwarning("Advertencia", "No hay datos para imprimir.")
            return

        entregado = self.entregado_entry.get().strip() or "Sin nombre"
        codigo = self.codigo_entry.get().strip()
        filename = f"Listado_Codigo_{codigo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = Path("exportados/listados")
        filepath.mkdir(parents=True, exist_ok=True)
        full_path = filepath / filename

        self.df_filtrado = self.df_filtrado[self.COLUMNAS]

        with pd.ExcelWriter(full_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("Listado")
            writer.sheets["Listado"] = worksheet
            worksheet.write("A1", "Listado por Código")
            worksheet.write("A2", f"Entregado a: {entregado}")
            worksheet.write("A3", f"Código consultado: {codigo}")
            self.df_filtrado.to_excel(writer, sheet_name="Listado", startrow=4, index=False)

        print_document(full_path, mode="codigo", config_columns={}, df=self.df_filtrado)
        capturar_log_bod1(f"Listado por código entregado a: {entregado} | Archivo: {full_path.name}", "info")
