from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk, simpledialog
import tkinter as tk
import os, re, json

# =================== Configuración básica ===================
load_config = lambda: {"carpeta_informes": str(Path.home() / "Documentos" / "StockFísico")}
save_config = lambda config: None

def obtener_descargas():
    return Path.home() / ("Downloads" if os.name == 'nt' else "Descargas")

def buscar_último_archivo(base: Path) -> Path | None:
    regex = re.compile(r"Informe_stock_fisico_(\d{8}_\d{6})")
    archivos = []
    for ext in ("*.xlsx", "*.xls"):
        archivos += [(f, regex.search(f.name).group(1)) for f in base.glob(ext) if regex.search(f.name)]
    return sorted(archivos, key=lambda x: x[1], reverse=True)[0][0] if archivos else None

def cargar_excel_stock(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, engine="openpyxl" if path.suffix == ".xlsx" else "xlrd")
        df.columns = df.columns.str.strip().str.lower()
        if 'fecha vencimiento' not in df.columns:
            raise ValueError("Falta la columna 'fecha vencimiento'")
        df['fecha vencimiento'] = pd.to_datetime(df['fecha vencimiento'], dayfirst=True, errors='coerce')
        return df
    except Exception as e:
        messagebox.showerror("Error cargando archivo", str(e))
        return pd.DataFrame()

# =================== Filtros Avanzados ===================
class FiltroAvanzado:
    def __init__(self, frame_visores):
        self.filtros = []
        self.frame_visores = frame_visores

    def agregar(self, columna, condicion, valor, actualizar_callback):
        if columna and valor:
            self.filtros.append((columna, condicion, valor.strip().lower()))
            self.refrescar_visores(actualizar_callback)

    def eliminar(self, idx, actualizar_callback):
        if 0 <= idx < len(self.filtros):
            self.filtros.pop(idx)
            self.refrescar_visores(actualizar_callback)

    def limpiar(self, actualizar_callback):
        self.filtros.clear()
        self.refrescar_visores(actualizar_callback)

    def aplicar(self, df):
        for col, cond, val in self.filtros:
            if col in df.columns:
                serie = df[col].astype(str).str.lower()
                if cond == 'Contiene':
                    df = df[serie.str.contains(val, na=False)]
                elif cond == 'Empieza con':
                    df = df[serie.str.startswith(val, na=False)]
                elif cond == 'Termina con':
                    df = df[serie.str.endswith(val, na=False)]
                elif cond == 'Igual a':
                    df = df[serie == val]
        return df

    def refrescar_visores(self, actualizar_callback):
        for widget in self.frame_visores.winfo_children():
            widget.destroy()
        for idx, (col, cond, val) in enumerate(self.filtros):
            chip = tk.Frame(self.frame_visores, bg="#E0E7FF", bd=1, relief="solid")
            chip.pack(side="left", padx=5, pady=2)
            lbl = tk.Label(chip, text=f"{col} {cond} {val}", bg="#E0E7FF", font=("Segoe UI", 9))
            lbl.pack(side="left", padx=(5,0))
            btn = tk.Button(chip, text="✖", command=lambda i=idx: self.eliminar(i, actualizar_callback),
                            bg="#F87171", fg="white", font=("Segoe UI", 8), relief="flat")
            btn.pack(side="right", padx=5)

# =================== CRUD sobre Treeview ===================
class TableEditor:
    def __init__(self, tree: ttk.Treeview, dataframe: pd.DataFrame):
        self.tree = tree
        self.df = dataframe
        self.setup()

    def setup(self):
        self.tree.bind('<Double-1>', self.edit_cell)

    def edit_cell(self, event):
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        col_idx = int(col.replace('#', '')) - 1
        x, y, width, height = self.tree.bbox(row_id, col)
        value = self.tree.item(row_id)['values'][col_idx]
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus()

        def guardar(event):
            nuevo = entry.get()
            self.tree.set(row_id, column=col, value=nuevo)
            idx = self.tree.index(row_id)
            self.df.iat[idx, col_idx] = nuevo
            entry.destroy()

        entry.bind('<Return>', guardar)
        entry.bind('<FocusOut>', lambda e: entry.destroy())

    def agregar_fila(self):
        nueva = pd.Series({col: '' for col in self.df.columns})
        self.df = pd.concat([self.df, nueva.to_frame().T], ignore_index=True)
        self.tree.insert("", "end", values=list(nueva))

    def eliminar_filas(self):
        seleccion = self.tree.selection()
        if not seleccion: return
        indices = [self.tree.index(item) for item in seleccion]
        for item in seleccion:
            self.tree.delete(item)
        self.df.drop(index=self.df.index[indices], inplace=True)
        self.df.reset_index(drop=True, inplace=True)

    def agregar_columna(self):
        nombre = simpledialog.askstring("Agregar columna", "Nombre de la nueva columna:")
        if nombre and nombre not in self.df.columns:
            self.df[nombre] = ''
            mostrar_en_treeview(self.tree, self.df)

    def eliminar_columna(self):
        nombre = simpledialog.askstring("Eliminar columna", "Nombre de la columna a eliminar:")
        if nombre in self.df.columns:
            self.df.drop(columns=[nombre], inplace=True)
            mostrar_en_treeview(self.tree, self.df)

# =================== Mostrar en Treeview ===================
def mostrar_en_treeview(tree: ttk.Treeview, df: pd.DataFrame):
    tree.delete(*tree.get_children())
    tree["columns"] = list(df.columns)
    tree["show"] = "headings"
    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    for _, row in df.iterrows():
        tree.insert("", "end", values=list(row))

# =================== Ventana Principal ===================
def crear_ventana_informes_stock():
    config = load_config()
    app = tk.Toplevel()
    app.title("Informes de Stock Físico")
    app.geometry("1300x780")

    frame_top = tk.Frame(app)
    frame_top.pack(pady=5)

    entry_archivo = tk.Entry(frame_top, width=80)
    entry_archivo.pack(side=tk.LEFT, padx=5)

    ttk.Button(frame_top, text="Generar Informes", command=lambda: generar()).pack(side=tk.LEFT, padx=5)
    ttk.Button(frame_top, text="Inventariado", command=lambda: inventariado()).pack(side=tk.LEFT, padx=5)

    combo_general = ttk.Combobox(frame_top, state="readonly", width=40)
    combo_general.pack(side=tk.LEFT, padx=5)

    frame_chips = tk.Frame(app)
    frame_chips.pack(pady=3, fill="x")

    columnas_disponibles = ['código', 'producto', 'ubicación', 'n° serie', 'lote', 'fecha vencimiento', 'saldo stock']
    condiciones_disponibles = ['Contiene', 'Empieza con', 'Termina con', 'Igual a']

    combo_columna = ttk.Combobox(frame_chips, values=columnas_disponibles, width=15, state="readonly")
    combo_columna.set("producto")
    combo_columna.pack(side=tk.LEFT, padx=5)

    combo_condicion = ttk.Combobox(frame_chips, values=condiciones_disponibles, width=12, state="readonly")
    combo_condicion.set("Contiene")
    combo_condicion.pack(side=tk.LEFT, padx=5)

    entry_valor = tk.Entry(frame_chips, width=20)
    entry_valor.pack(side=tk.LEFT, padx=5)

    filtros_aplicados = FiltroAvanzado(frame_chips)

    tree = ttk.Treeview(app)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    informes = {}
    editor = None

    def actualizar(event=None):
        nonlocal editor
        clave = combo_general.get()
        if clave in informes:
            df = informes[clave].copy()
            df = filtros_aplicados.aplicar(df)
            mostrar_en_treeview(tree, df)
            editor = TableEditor(tree, df)

    def agregar_filtro():
        col = combo_columna.get()
        cond = combo_condicion.get()
        val = entry_valor.get().strip()
        if col and val:
            filtros_aplicados.agregar(col, cond, val, actualizar)
            entry_valor.delete(0, tk.END)

    def generar():
        carpeta = Path(config.get("carpeta_informes", ""))
        if not carpeta.exists():
            carpeta = Path(filedialog.askdirectory(title="Selecciona carpeta de informes de stock"))
            config["carpeta_informes"] = str(carpeta)
            save_config(config)

        archivo = buscar_último_archivo(carpeta)
        if not archivo:
            messagebox.showwarning("Archivo no encontrado", f"No se encontró archivo en {carpeta}")
            return

        entry_archivo.delete(0, tk.END)
        entry_archivo.insert(0, str(archivo))

        df = cargar_excel_stock(archivo)
        if df.empty:
            return

        informes.clear()
        informes["Inventariado"] = df[df['ubicación'].notna()].sort_values(by='ubicación')
        combo_general.set("Inventariado")
        actualizar()

    def inventariado():
        ubic = simpledialog.askstring("Inventariado", "Ubicación base para filtrar (ej: 14-B):")
        if not ubic:
            return
        filtros_aplicados.limpiar(actualizar)
        filtros_aplicados.agregar('ubicación', 'Empieza con', ubic, actualizar)
        filtros_aplicados.agregar('saldo stock', 'Mayor que', '0', actualizar)
        combo_general.set("Inventariado")
        actualizar()

    ttk.Button(frame_chips, text="➕ Agregar Filtro", command=agregar_filtro).pack(side=tk.LEFT, padx=5)
    ttk.Button(frame_chips, text="🧹 Mostrar Todo", command=lambda: filtros_aplicados.limpiar(actualizar)).pack(side=tk.LEFT, padx=5)

    def exportar_inventariado():
        clave = combo_general.get()
        if clave not in informes:
            messagebox.showwarning("Exportar", "Selecciona un informe.")
            return
        df_exportar = filtros_aplicados.aplicar(informes[clave].copy())
        if df_exportar.empty:
            messagebox.showinfo("Vacío", "No hay datos para exportar.")
            return
        ubicacion = "general"
        if filtros_aplicados.filtros:
            for col, cond, val in filtros_aplicados.filtros:
                if col == "ubicación":
                    ubicacion = val.replace(" ", "_")
                    break
        nombre = f"inventariado_{ubicacion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        carpeta_export = Path(config.get("carpeta_informes", obtener_descargas()))
        carpeta_export.mkdir(parents=True, exist_ok=True)
        ruta = carpeta_export / nombre
        try:
            df_exportar.to_excel(ruta, index=False)
            messagebox.showinfo("Exportado", f"Inventariado guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))

    ttk.Button(frame_chips, text="📤 Exportar Inventariado", command=exportar_inventariado).pack(side=tk.LEFT, padx=5)

    generar()
    app.mainloop()
