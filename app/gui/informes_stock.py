# app/gui/informes_stock.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import pandas as pd

from app.core.excel_processor import load_excel, apply_transformation
from app.db.utils_db import save_file_history
from app.core.logger_bod1 import capturar_log_bod1
from app.utils.utils import load_config


def crear_ventana_informes_stock(root=None):
    """
    Abre una ventana Toplevel con:
    - Selector de rango de fechas (Fecha Desde / Fecha Hasta)
    - Botón para cargar un Excel de stock físico
    - Treeview para mostrar los datos filtrados
    - Botón para exportar el filtrado a Excel
    """
    # ------------------------------
    # Inicialización de la ventana
    # ------------------------------
    if root is None:
        root = tk._default_root if tk._default_root else tk.Tk()
    ventana = tk.Toplevel(root)
    ventana.title("Informes de Stock Físico")
    ventana.geometry("900x600")

    # ------------------------------
    # Cargar configuración de columnas
    # ------------------------------
    config_columns = load_config()
    mode = "listados"  
    # Si tienes un modo específico para stock, añádelo en excel_printer_config.json y cámbialo aquí:
    # mode = "stock"

    # ------------------------------
    # Frame de controles (fecha + botones)
    # ------------------------------
    frame_ctrl = ttk.Frame(ventana, padding=10)
    frame_ctrl.pack(fill="x", padx=10, pady=5)

    ttk.Label(frame_ctrl, text="Fecha Desde:").pack(side="left")
    fecha_desde = DateEntry(frame_ctrl, width=12, date_pattern='yyyy-MM-dd')
    fecha_desde.pack(side="left", padx=(5, 20))

    ttk.Label(frame_ctrl, text="Fecha Hasta:").pack(side="left")
    fecha_hasta = DateEntry(frame_ctrl, width=12, date_pattern='yyyy-MM-dd')
    fecha_hasta.pack(side="left", padx=(5, 20))

    def cargar_y_filtrar():
        ruta = filedialog.askopenfilename(
            title="Seleccionar informe de stock físico",
            filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")]
        )
        if not ruta:
            return

        try:
            capturar_log_bod1(f"Archivo seleccionado: {ruta}", nivel="info")
            # 1) Carga del Excel con config_columns y mode
            df = load_excel(ruta, config_columns, mode)
            # 2) Aplicar transformación (drop/sum/format)
            df_transformed, total = apply_transformation(df, config_columns, mode)
            # 3) Filtrar por rango de fechas (asume que existe columna 'Fecha')
            df_transformed['Fecha'] = pd.to_datetime(df_transformed['Fecha'], errors='coerce')
            desde = pd.to_datetime(fecha_desde.get_date())
            hasta = pd.to_datetime(fecha_hasta.get_date())
            df_filtrado = df_transformed[
                (df_transformed['Fecha'] >= desde) & 
                (df_transformed['Fecha'] <= hasta)
            ]
        except Exception as e:
            capturar_log_bod1(f"Error al procesar Excel: {e}", nivel="error")
            messagebox.showerror("Error", f"No se pudo procesar el archivo:\n{e}")
            return

        # 4) Mostrar en el Treeview
        for row in tree.get_children():
            tree.delete(row)
        for _, fila in df_filtrado.reset_index(drop=True).iterrows():
            tree.insert("", "end", values=list(fila))

        # 5) Guardar historial en la base de datos
        try:
            save_file_history(ruta, modo=mode)
        except Exception as e:
            capturar_log_bod1(f"Error al guardar historial: {e}", nivel="error")

    btn_cargar = ttk.Button(frame_ctrl, text="Cargar y Filtrar", command=cargar_y_filtrar)
    btn_cargar.pack(side="left", padx=5)

    def exportar_filtrado():
        # Extraer filas mostradas en el Treeview
        rows = [tree.item(i)["values"] for i in tree.get_children()]
        if not rows:
            messagebox.showwarning("Aviso", "No hay datos para exportar.")
            return
        df_export = pd.DataFrame(rows, columns=cols)
        ruta_save = filedialog.asksaveasfilename(
            title="Guardar informe filtrado",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not ruta_save:
            return
        try:
            df_export.to_excel(ruta_save, index=False)
            capturar_log_bod1(f"Informe exportado: {ruta_save}", nivel="info")
            messagebox.showinfo("Éxito", f"Informe exportado a:\n{ruta_save}")
        except Exception as e:
            capturar_log_bod1(f"Error al exportar: {e}", nivel="error")
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    btn_exportar = ttk.Button(frame_ctrl, text="Exportar a Excel", command=exportar_filtrado)
    btn_exportar.pack(side="left", padx=5)

    # ------------------------------
    # Treeview para mostrar los datos
    # ------------------------------
    # Ajusta 'cols' con los nombres reales de tus columnas
    cols = list(config_columns.get(mode, {}).get("mantener_formato", []))  
    if not cols:
        # Si no tienes 'mantener_formato' definido, tomamos todas las columnas del DataFrame tras cargar:
        cols = ["Columna1", "Columna2", "Columna3"]  # reemplaza manualmente

    tree = ttk.Treeview(ventana, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=100, anchor="center")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------
    # Modalidad de la ventana
    # ------------------------------
    ventana.transient(root)
    ventana.grab_set()
    ventana.focus_set()
    ventana.wait_window()
