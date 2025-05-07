import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime

class ConsultaUbicacionApp(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Consulta por Ubicación")
        self.geometry("1000x500")
        self.configure(bg="#d7e3ea")

        tk.Label(self, text="Consulta Stock por Ubicacion", font=("Segoe UI", 18, "bold", "italic"),
                 fg="red", bg="#d7e3ea").pack(pady=10)

        filtro_frame = tk.Frame(self, bg="#d7e3ea")
        filtro_frame.pack(pady=10)

        tk.Label(filtro_frame, text="Ubicación:", font=("Segoe UI", 10, "bold"),
                 fg="red", bg="#d7e3ea").grid(row=0, column=0)
        self.ubicacion_entry = ttk.Entry(filtro_frame, width=20)
        self.ubicacion_entry.grid(row=0, column=1, padx=5)
        ttk.Button(filtro_frame, text="Buscar", command=self.buscar).grid(row=0, column=2, padx=5)

        self.tree = ttk.Treeview(self, columns=["Código", "Producto", "Bodega", "Ubicación", "Lote", "Fecha Vencimiento", "Saldo stock"], show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        self.total_label = tk.Label(self, text="Stock Total: 0", font=("Segoe UI", 12, "bold"),
                                    fg="red", bg="#d7e3ea")
        self.total_label.pack(pady=5)

        ttk.Button(self, text="Imprimir", command=self.exportar).pack(pady=5)
        self.df = pd.read_excel("Informe_stock_fisico_20250428_124147.xlsx")

    def buscar(self):
        ubicacion = self.ubicacion_entry.get().strip()
        if not ubicacion:
            messagebox.showwarning("Atención", "Debe ingresar una ubicación.")
            return
        filtrado = self.df[self.df["Ubicación"].astype(str) == ubicacion]
        self.tree.delete(*self.tree.get_children())
        for _, row in filtrado.iterrows():
            self.tree.insert("", "end", values=list(row.values))
        total = filtrado["Saldo stock"].sum()
        self.total_label.config(text=f"Stock Total: {total}")

    def exportar(self):
        ubicacion = self.ubicacion_entry.get().strip()
        if not ubicacion:
            return
        filtrado = self.df[self.df["Ubicación"].astype(str) == ubicacion]
        nombre = f"Consulta_ubicacion_{ubicacion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filtrado.to_excel(nombre, index=False)
        messagebox.showinfo("Exportado", f"Se guardó como {nombre}")