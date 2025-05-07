import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime
from pathlib import Path
import tempfile
import os
import pythoncom
from win32com.client import Dispatch

class ConsultaCodigoApp(tk.Toplevel):
    COLUMNAS = ["Código", "Producto", "Bodega", "Ubicación", "Lote", "Fecha Vencimiento", "Saldo stock"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Consulta por Código")
        self.geometry("1100x500")
        self.configure(bg="#e6e9e7")

        tk.Label(self, text="Consulta por Codigo", font=("Segoe UI", 18, "bold", "italic"),
                 fg="red", bg="#e6e9e7").pack(pady=10)

        filtro_frame = tk.Frame(self, bg="#e6e9e7")
        filtro_frame.pack(pady=5)

        tk.Label(filtro_frame, text="Código:", font=("Segoe UI", 10, "bold"),
                 fg="red", bg="#e6e9e7").grid(row=0, column=0)
        self.codigo_entry = ttk.Entry(filtro_frame, width=20)
        self.codigo_entry.grid(row=0, column=1, padx=5)
        ttk.Button(filtro_frame, text="Buscar", command=self.buscar).grid(row=0, column=2, padx=5)

        self.tree = ttk.Treeview(self, columns=self.COLUMNAS, show="headings")
        for col in self.COLUMNAS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor=tk.CENTER)
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        self.total_label = tk.Label(self, text="Total Stock: 0", font=("Segoe UI", 12, "bold"),
                                    fg="red", bg="#e6e9e7")
        self.total_label.pack(pady=5)

        ttk.Button(self, text="Imprimir", command=self.imprimir).pack(pady=5)

        self.df = self.cargar_ultimo_excel()

    def cargar_ultimo_excel(self):
        descargas = Path.home() / "Downloads"
        archivos = sorted(descargas.glob("Informe_stock_fisico_*.xlsx"), key=os.path.getmtime, reverse=True)
        if not archivos:
            messagebox.showerror("Error", "No se encontró archivo de stock en Descargas.")
            self.destroy()
            return pd.DataFrame()
        return pd.read_excel(archivos[0])

    def buscar(self):
        codigo = self.codigo_entry.get().strip()
        if not codigo or self.df.empty:
            return

        self.resultado = self.df[self.df["Código"].astype(str) == codigo]
        self.tree.delete(*self.tree.get_children())

        for _, row in self.resultado.iterrows():
            valores = [row.get(col, "") for col in self.COLUMNAS]
            self.tree.insert("", "end", values=valores)

        total = self.resultado["Saldo stock"].sum()
        self.total_label.config(text=f"Total Stock: {total}")

    def imprimir(self):
        if self.resultado.empty:
            messagebox.showwarning("Advertencia", "No hay resultados para imprimir.")
            return

        temp_excel = Path(tempfile.gettempdir()) / f"listado_codigo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.resultado.to_excel(temp_excel, index=False)

        try:
            pythoncom.CoInitialize()
            excel = Dispatch("Excel.Application")
            excel.Visible = False
            wb = excel.Workbooks.Open(str(temp_excel))
            ws = wb.Sheets(1)
            ws.Columns.AutoFit()

            ws.PageSetup.Orientation = 2  # Horizontal
            ws.PageSetup.Zoom = False
            ws.PageSetup.FitToPagesWide = 1
            ws.PageSetup.FitToPagesTall = False

            fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            total = self.resultado["Saldo stock"].sum()
            ws.PageSetup.CenterFooter = f"&\"Arial,Bold\"&8 Impreso: {fecha_hora}  |  Total Stock: {total}"

            ws.PrintOut()
            wb.Close(SaveChanges=False)
            excel.Quit()
            messagebox.showinfo("Impresión", "Listado enviado a impresora correctamente.")
        except Exception as e:
            messagebox.showerror("Error de impresión", f"No se pudo imprimir:\n{e}")
        finally:
            pythoncom.CoUninitialize()
