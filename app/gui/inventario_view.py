import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from pathlib import Path

from app.utils.utils import guardar_ultimo_path, load_config_from_file
from app.core.logger_eventos import capturar_log_bod1
from app.printer import printer_inventario_codigo, printer_inventario_ubicacion

VISIBLE_COLUMNS = [
    "Código", "Producto", "Bodega", "Ubicación",
    "N° Serie", "Lote", "Fecha Vencimiento", "Saldo Stock"
]

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

    def _crear_widgets(self):
        top_frame = tk.Frame(self, bg="#F9FAFB")
        top_frame.pack(pady=10)

        tk.Label(top_frame, text="Buscar por Código o Ubicación:", bg="#F9FAFB").pack(side="left", padx=5)
        self.entry_busqueda = tk.Entry(top_frame, width=40)
        self.entry_busqueda.pack(side="left", padx=5)
        self.entry_busqueda.bind("<Return>", lambda e: self._filtrar())

        ttk.Button(top_frame, text="Buscar", command=self._filtrar).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Buscar Archivo Excel", command=self._recargar_archivo).pack(side="left", padx=5)
        ttk.Button(top_frame, text="🖨️ Imprimir Resultado", command=self._imprimir_resultado).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self, columns=VISIBLE_COLUMNS, show="headings", height=25)
        for col in VISIBLE_COLUMNS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

    def _cargar_o_pedir_archivo(self):
        config = load_config_from_file()
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
            filetypes=[("Archivos Excel", "*.xls *.xlsx")]
        )
        if ruta_archivo:
            guardar_ultimo_path(ruta_archivo, clave="archivo_inventario")
            self._leer_excel(Path(ruta_archivo))

    def _leer_excel(self, path: Path):
        try:
            df = pd.read_excel(path)
            if not all(col in df.columns for col in VISIBLE_COLUMNS):
                raise ValueError(f"Faltan columnas requeridas: {set(VISIBLE_COLUMNS) - set(df.columns)}")
            self.df = df
            self.df_filtrado = pd.DataFrame()
            self._actualizar_tree(self.df)
            capturar_log_bod1(f"Archivo de inventario cargado: {path}", "info")
            messagebox.showinfo("Inventario", f"Archivo cargado correctamente: {path.name}")
        except Exception as e:
            capturar_log_bod1(f"Error al cargar inventario: {e}", "error")
            messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")
            self.df = pd.DataFrame()

    def _filtrar(self):
        termino = self.entry_busqueda.get().strip().lower()
        if not termino:
            messagebox.showinfo("Buscar", "Ingrese un término de búsqueda.")
            return

        df_codigo = self.df[self.df["Código"].astype(str).str.lower().str.contains(termino)]
        df_ubicacion = self.df[self.df["Ubicación"].astype(str).str.lower().str.contains(termino)]

        if not df_codigo.empty:
            self.df_filtrado = df_codigo
            self.tipo_busqueda = "codigo"
        elif not df_ubicacion.empty:
            self.df_filtrado = df_ubicacion
            self.tipo_busqueda = "ubicacion"
        else:
            self.df_filtrado = pd.DataFrame()
            self.tipo_busqueda = None

        self._actualizar_tree(self.df_filtrado)

    def _actualizar_tree(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        if df.empty:
            return
        for row in df[VISIBLE_COLUMNS].itertuples(index=False):
            self.tree.insert("", "end", values=row)

    def _imprimir_resultado(self):
        if self.df_filtrado.empty:
            messagebox.showwarning("Sin datos", "No hay resultados filtrados para imprimir.")
            return

        try:
            df_to_print = self.df_filtrado.copy()
            capturar_log_bod1(f"Generando impresión de inventario ({self.tipo_busqueda}) con {len(df_to_print)} registros.", "info")

            if self.tipo_busqueda == "codigo":
                printer_inventario_codigo.print_inventario_codigo(df=df_to_print)
            elif self.tipo_busqueda == "ubicacion":
                printer_inventario_ubicacion.print_inventario_ubicacion(df=df_to_print)
            else:
                messagebox.showwarning("Tipo de búsqueda", "Debe realizar una búsqueda válida antes de imprimir.")

        except Exception as e:
            capturar_log_bod1(f"Error al imprimir inventario: {e}", "error")
            messagebox.showerror("Error", f"No se pudo imprimir:\n{e}")
