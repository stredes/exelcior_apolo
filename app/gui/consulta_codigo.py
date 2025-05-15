# app/gui/consulta_codigo.py

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from pathlib import Path
from datetime import datetime
from app.printer.print_router import print_document  # ✅ Correcto y multiplataforma
from app.core.logger_bod1 import capturar_log_bod1


class ConsultaCodigoApp(tk.Toplevel):
    COLUMNS = ["Código", "Producto", "Bodega", "Ubicación", "Lote", "Fecha Vencimiento", "Saldo stock"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Consulta por Código")
        self.geometry("1100x600")
        self.configure(bg="#e6e9e7")

        tk.Label(self, text="Consulta Stock por Código", font=("Segoe UI", 18, "bold", "italic"),
                 fg="red", bg="#e6e9e7").pack(pady=10)

        filtro_frame = tk.Frame(self, bg="#e6e9e7")
        filtro_frame.pack(pady=5)

        tk.Label(filtro_frame, text="Código:", font=("Segoe UI", 10, "bold"),
                 fg="red", bg="#e6e9e7").grid(row=0, column=0)
        self.codigo_entry = ttk.Entry(filtro_frame, width=20)
        self.codigo_entry.grid(row=0, column=1, padx=5)
        ttk.Button(filtro_frame, text="Buscar", command=self.buscar).grid(row=0, column=2, padx=5)

        tk.Label(filtro_frame, text="Entregado a:", font=("Segoe UI", 10, "bold"),
                 fg="red", bg="#e6e9e7").grid(row=0, column=3)
        self.entregado_entry = ttk.Entry(filtro_frame, width=30)
        self.entregado_entry.grid(row=0, column=4, padx=5)

        self.tree = ttk.Treeview(self, columns=self.COLUMNS, show="headings")
        for col in self.COLUMNS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor=tk.CENTER)
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        self.total_label = tk.Label(self, text="Stock Total: 0", font=("Segoe UI", 12, "bold"),
                                    fg="red", bg="#e6e9e7")
        self.total_label.pack(pady=5)

        ttk.Button(self, text="Imprimir", command=self.exportar).pack(pady=5)

        self.df = self._cargar_excel_reciente()

    def _cargar_excel_reciente(self):
        carpeta_descargas = Path.home() / "Downloads"
        archivos = list(carpeta_descargas.glob("Informe_stock_fisico_*.xlsx"))
        if not archivos:
            messagebox.showerror("Error", "No se encontró ningún archivo de stock físico en Descargas.")
            self.destroy()
            return pd.DataFrame()

        archivo_mas_reciente = max(archivos, key=lambda f: f.stat().st_mtime)
        df = pd.read_excel(archivo_mas_reciente)

        columnas_faltantes = [col for col in self.COLUMNS if col not in df.columns]
        if columnas_faltantes:
            messagebox.showerror("Error", f"Faltan columnas: {columnas_faltantes}")
            self.destroy()
            return pd.DataFrame()

        self.archivo_fuente = archivo_mas_reciente
        return df

    def buscar(self):
        codigo = self.codigo_entry.get().strip()
        if not codigo or self.df.empty:
            return

        filtrado = self.df[self.df["Código"].astype(str).str.strip().str.lower() == codigo.lower()]
        self.tree.delete(*self.tree.get_children())

        for _, row in filtrado.iterrows():
            self.tree.insert("", "end", values=[row.get(col, "") for col in self.COLUMNS])

        total = filtrado["Saldo stock"].sum()
        self.total_label.config(text=f"Stock Total: {total}")
        self.df_filtrado = filtrado

    def exportar(self):
        if not hasattr(self, "df_filtrado") or self.df_filtrado.empty:
            messagebox.showwarning("Advertencia", "No hay datos para exportar.")
            return

        entregado = self.entregado_entry.get().strip() or "Sin nombre"
        codigo = self.codigo_entry.get().strip() or "No especificado"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Listado_Codigo_{timestamp}.xlsx"
        output_dir = Path("exportados/listados")
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename

        self.df_filtrado = self.df_filtrado[self.COLUMNS]

        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("Listado")
            writer.sheets["Listado"] = worksheet
            worksheet.write("A1", "Listado por Código")
            worksheet.write("A2", f"Entregado a: {entregado}")
            worksheet.write("A3", f"Código consultado: {codigo}")
            self.df_filtrado.to_excel(writer, sheet_name="Listado", startrow=4, index=False)

        print_document(filepath, mode="urbano", config_columns={}, df=self.df_filtrado)
        capturar_log_bod1(f"Listado por código entregado a: {entregado} | Archivo: {filepath.name}", "info")
