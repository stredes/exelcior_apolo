import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from pathlib import Path

from app.utils.utils import guardar_ultimo_path, load_config_from_file
from app.core.logger_eventos import capturar_log_bod1
from app.printer import printer_inventario_codigo, printer_inventario_ubicacion

VISIBLE_COLUMNS = [
    "Código", "Producto", "Bodega", "Ubicación",
    "N° Serie", "Lote", "Fecha Vencimiento", "Saldo stock"
]


class InventarioView(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventario - Consulta")
        self.geometry("1200x700")
        self.config(bg="#F9FAFB")

        self.df = self._cargar_df_inventario()
        self._crear_widgets()

    def _crear_widgets(self):
        top_frame = tk.Frame(self, bg="#F9FAFB")
        top_frame.pack(pady=10)

        tk.Label(top_frame, text="Buscar por Código o Ubicación:", bg="#F9FAFB").pack(side="left", padx=5)
        self.entry_busqueda = tk.Entry(top_frame, width=40)
        self.entry_busqueda.pack(side="left", padx=5)
        self.entry_busqueda.bind("<Return>", lambda e: self._filtrar())

        ttk.Button(top_frame, text="Buscar", command=self._filtrar).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Buscar Archivo Excel", command=self._recargar_archivo).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Imprimir Resultado", command=self._imprimir_resultado).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self, columns=VISIBLE_COLUMNS, show="headings", height=25)
        for col in VISIBLE_COLUMNS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        self._actualizar_tree(self.df)

    def _recargar_archivo(self):
        ruta = self._buscar_archivo_excel()
        if ruta:
            self.df = self._cargar_df_inventario()
            self._actualizar_tree(self.df)

    def _buscar_archivo_excel(self):
        ruta_archivo = filedialog.askopenfilename(
            title="Selecciona el archivo de inventario",
            filetypes=[("Archivos Excel", "*.xls *.xlsx")]
        )
        if ruta_archivo:
            guardar_ultimo_path(ruta_archivo, clave="archivo_inventario")
            capturar_log_bod1(f"Ruta de inventario guardada: {ruta_archivo}", "info")
        return ruta_archivo

    def _cargar_df_inventario(self):
        config = load_config_from_file()
        ruta = config.get("archivo_inventario")
        if not ruta or not Path(ruta).exists():
            ruta = self._buscar_archivo_excel()
        if not ruta:
            return pd.DataFrame()
        try:
            df = pd.read_excel(ruta)
            capturar_log_bod1(f"Archivo de inventario cargado: {ruta}", "info")
            return df
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")
            capturar_log_bod1(f"Error al cargar inventario: {e}", "error")
            return pd.DataFrame()

    def _filtrar(self):
        termino = self.entry_busqueda.get().strip().lower()
        if not termino:
            messagebox.showinfo("Buscar", "Ingrese un término de búsqueda.")
            return
        df_filtrado = self.df[
            self.df["Código"].astype(str).str.lower().str.contains(termino) |
            self.df["Ubicación"].astype(str).str.lower().str.contains(termino)
        ]
        self._actualizar_tree(df_filtrado)

    def _actualizar_tree(self, df):
        self.tree.delete(*self.tree.get_children())
        if df.empty:
            return
        if not all(col in df.columns for col in VISIBLE_COLUMNS):
            messagebox.showerror("Error", "El archivo no contiene todas las columnas necesarias.")
            return
        for row in df[VISIBLE_COLUMNS].itertuples(index=False):
            self.tree.insert("", "end", values=row)

    def _imprimir_resultado(self):
        if self.df.empty:
            messagebox.showwarning("Sin datos", "No hay datos para imprimir.")
            return
        df_filtrado = [
            self.tree.item(item)["values"]
            for item in self.tree.get_children()
        ]
        if not df_filtrado:
            messagebox.showinfo("Impresión", "No hay resultados filtrados para imprimir.")
            return
        try:
            df_to_print = pd.DataFrame(df_filtrado, columns=VISIBLE_COLUMNS)
            termino = self.entry_busqueda.get().strip().lower()
            if any(termino in str(c).lower() for c in df_to_print["Código"]):
                printer_inventario_codigo.print_inventario_codigo(
                    Path("inventario_codigo.xlsx"), {}, df_to_print
                )
            else:
                printer_inventario_ubicacion.print_inventario_ubicacion(
                    Path("inventario_ubicacion.xlsx"), {}, df_to_print
                )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo imprimir el archivo:\n{e}")
