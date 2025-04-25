# Reescritura optimizada del módulo de informes de stock físico con autocarga, configuración dinámica y CRUD extendido
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk, simpledialog
import tkinter as tk
import os, re, json

# Placeholder para configuración externa
load_config = lambda: {"carpeta_informes": str(Path.home() / "Documentos" / "StockFísico")}
save_config = lambda config: None

# =================== Funciones Auxiliares ===================
def obtener_descargas():
    return Path.home() / ("Downloads" if os.name == 'nt' else "Descargas")

def buscar_último_archivo(base: Path) -> Path | None:
    regex = re.compile(r"Informe_stock_fisico_(\d{8}_\d{6})\.xlsx")
    archivos = [(f, regex.search(f.name).group(1)) for f in base.glob("Informe_stock_fisico_*.xlsx") if regex.search(f.name)]
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

# =================== Configuración personalizada ===================
def cargar_configuracion_columnas_stock() -> dict:
    config_path = Path.home() / ".exelcior_stock_config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_configuracion_columnas_stock(config_dict: dict):
    config_path = Path.home() / ".exelcior_stock_config.json"
    try:
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    except Exception as e:
        messagebox.showerror("Error guardando configuración", str(e))

# =================== Lógica de Informes ===================
def generar_informes(df: pd.DataFrame, dias: int = 60, ubicaciones=None, config_columns: dict = None) -> dict:
    hoy = datetime.today()
    proximo = hoy + timedelta(days=dias)
    out = {}
    try:
        out["Caducidad Próxima"] = df[df['fecha vencimiento'].between(hoy, proximo)].sort_values(by='fecha vencimiento', ascending=False)
        out["Productos Vencidos"] = df[df['fecha vencimiento'] < hoy].sort_values(by='fecha vencimiento', ascending=False)
        out["Múltiples Lotes"] = df.groupby('código').filter(lambda x: x['lote'].nunique() > 1).sort_values(by='saldo stock', ascending=False)
        if 'bodega' in df:
            out["Bodega Temporal"] = df[df['bodega'].str.contains("temporal", case=False, na=False)].sort_values(by='saldo stock', ascending=False)
        if 'reserva' in df:
            out["Stock Reservado"] = df[df['reserva'] > 0].sort_values(by='reserva', ascending=False)
        if 'saldo stock' in df:
            out["Stock por Producto"] = df.groupby('producto')['saldo stock'].sum().reset_index().sort_values(by='saldo stock', ascending=False)
        if 'ubicación' in df:
            ubicaciones_validas = sorted(df['ubicación'].dropna().unique())
            df_ubic = df.copy()
            if config_columns and 'stock_general' in config_columns:
                columnas = config_columns['stock_general']
                df_ubic = df_ubic[[col for col in columnas if col in df_ubic.columns]]
            df_ubic['fecha vencimiento'] = df_ubic['fecha vencimiento'].dt.strftime('%d/%m/%Y')
            out["Ubicación: Todas"] = df_ubic.sort_values(by='saldo stock', ascending=False)
            for ubic in ubicaciones_validas:
                if ubicaciones and not any(ubic.startswith(u) for u in ubicaciones):
                    continue
                filtro = df[df['ubicación'].str.startswith(ubic)].copy()
                if config_columns and 'stock_ubicacion' in config_columns:
                    columnas = config_columns['stock_ubicacion']
                    filtro = filtro[[col for col in columnas if col in filtro.columns]]
                filtro['fecha vencimiento'] = filtro['fecha vencimiento'].dt.strftime('%d/%m/%Y')
                out[f"Ubicación: {ubic}"] = filtro.sort_values(by='saldo stock', ascending=False)
    except Exception as e:
        messagebox.showerror("Error generando informes", str(e))
    return out

# =================== UI Helpers ===================
def mostrar_en_treeview(tree: ttk.Treeview, df: pd.DataFrame):
    tree.delete(*tree.get_children())
    tree["columns"] = list(df.columns)
    tree["show"] = "headings"
    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    for _, row in df.iterrows():
        tree.insert("", "end", values=list(row))

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
        if region != 'cell': return
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
# =================== Ventana Principal ===================
def crear_ventana_informes_stock():
    config = load_config()
    app = tk.Toplevel()
    app.title("Informes de Stock Físico")
    app.geometry("1200x700")

    frame_config = tk.Frame(app)
    frame_config.pack(pady=3)

    def cambiar_carpeta():
        nueva = filedialog.askdirectory(title="Editar carpeta de informes")
        if nueva:
            config["carpeta_informes"] = nueva
            save_config(config)
            messagebox.showinfo("Configuración actualizada", f"Nueva carpeta: {nueva}")
            generar()

    tk.Button(frame_config, text="📁 Cambiar carpeta de informes", command=cambiar_carpeta).pack(side=tk.RIGHT, padx=10)


    frame_top = tk.Frame(app)
    frame_top.pack(pady=5)

    tk.Label(frame_top, text="Archivo cargado:").pack(side=tk.LEFT)
    entry_archivo = tk.Entry(frame_top, width=80)
    entry_archivo.pack(side=tk.LEFT, padx=5)

    frame_filtros = tk.LabelFrame(app, text="Opciones de Informe")
    frame_filtros.pack(pady=5, fill="x", padx=10)

    combo_general = ttk.Combobox(frame_filtros, state="readonly", width=40)
    combo_general.pack(side=tk.LEFT, padx=5)

    combo_ubic = ttk.Combobox(frame_filtros, state="readonly", width=30)
    combo_ubic.pack(side=tk.LEFT, padx=5)

    entry_busqueda = tk.Entry(frame_filtros, width=25)
    entry_busqueda.pack(side=tk.LEFT, padx=5)
    entry_busqueda.insert(0, "Buscar...")

    tree = ttk.Treeview(app)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    frame_crud = tk.Frame(app)
    frame_crud.pack(pady=5)

    informes = {}
    editor = None

    def actualizar(event=None):
        nonlocal editor
        clave = combo_general.get() or combo_ubic.get()
        if clave in informes:
            df = informes[clave]
            if entry_busqueda.get().strip() not in ("", "Buscar..."):
                texto = entry_busqueda.get().strip().lower()
                df = df[df.apply(lambda r: texto in str(r.values).lower(), axis=1)]
            mostrar_en_treeview(tree, df)
            editor = TableEditor(tree, informes[clave])

    def generar():
        config = load_config()
        carpeta_configurada = config.get("carpeta_informes", "")
        carpeta = Path(carpeta_configurada)

        if not carpeta.exists():
            nueva = filedialog.askdirectory(title="Selecciona carpeta de informes de stock")
            if not nueva:
                messagebox.showwarning("Carpeta requerida", "Debes seleccionar una carpeta para continuar.")
                return
            carpeta = Path(nueva)
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
        informes.update(generar_informes(df))

        generales = sorted(k for k in informes if not k.startswith("Ubicación: "))
        por_ubic = sorted(k for k in informes if k.startswith("Ubicación: "))

        combo_general["values"] = generales
        combo_ubic["values"] = por_ubic
        if generales:
            combo_general.current(0)
        if por_ubic:
            combo_ubic.current(0)
        actualizar()

    def exportar():
        clave = combo_general.get() or combo_ubic.get()
        if clave not in informes:
            messagebox.showwarning("Exportar", "Selecciona un informe.")
            return
        df = informes[clave]
        if df.empty:
            messagebox.showinfo("Vacío", "No hay datos para exportar.")
            return
        nombre = f"{clave.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        config = load_config()
        carpeta = Path(config.get("carpeta_informes", obtener_descargas()))
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / nombre
        try:
            df.to_excel(ruta, index=False)
            messagebox.showinfo("Exportado", f"Guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))

    tk.Button(frame_crud, text="➕ Fila", command=lambda: editor.agregar_fila() if editor else None).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_crud, text="❌ Fila", command=lambda: editor.eliminar_filas() if editor else None).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_crud, text="➕ Columna", command=lambda: editor.agregar_columna() if editor else None).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_crud, text="🗑️ Columna", command=lambda: editor.eliminar_columna() if editor else None).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_crud, text="Exportar", command=exportar).pack(side=tk.LEFT, padx=5)

    combo_general.bind("<<ComboboxSelected>>", actualizar)
    combo_ubic.bind("<<ComboboxSelected>>", actualizar)
    entry_busqueda.bind("<KeyRelease>", actualizar)

    generar()
    app.mainloop()
