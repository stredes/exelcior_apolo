import pandas as pd
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import difflib

from app.utils.utils import load_config, save_config
from app.core.logger_bod1 import capturar_log_bod1

def cargar_codigos_postales():
    try:
        config = load_config()
        ruta_guardada = config.get("postal_file")

        if ruta_guardada and Path(ruta_guardada).exists():
            df = pd.read_excel(ruta_guardada)
        else:
            ruta_manual = filedialog.askopenfilename(
                title="Selecciona el archivo 'Codigos Postales SAM.xlsx'",
                filetypes=[("Excel Files", "*.xlsx *.xls")]
            )
            if not ruta_manual:
                raise FileNotFoundError("Archivo no seleccionado.")
            df = pd.read_excel(ruta_manual)
            config["postal_file"] = ruta_manual
            save_config(config)
            capturar_log_bod1(f"Ruta del archivo postal guardada: {ruta_manual}", "info")

        df.columns = [col.strip().lower() for col in df.columns]
        return df

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el archivo de códigos postales:\n{e}")
        capturar_log_bod1(f"Error al cargar códigos postales: {e}", "error")
        return pd.DataFrame()

def crear_widget_postal(parent):
    df_codigos = cargar_codigos_postales()

    frame = tk.LabelFrame(parent, text="📦 Código Postal por Comuna", padx=10, pady=10)
    frame.pack(padx=10, pady=10, fill="x", expand=False)

    entry_query = tk.Entry(frame, width=40, fg="gray")
    placeholder = "Ej: Chillán"
    entry_query.insert(0, placeholder)
    entry_query.pack(pady=5)

    def on_focus_in(event):
        if entry_query.get() == placeholder:
            entry_query.delete(0, tk.END)
            entry_query.config(fg="black")

    def on_focus_out(event):
        if entry_query.get() == "":
            entry_query.insert(0, placeholder)
            entry_query.config(fg="gray")

    entry_query.bind("<FocusIn>", on_focus_in)
    entry_query.bind("<FocusOut>", on_focus_out)

    listbox_resultados = tk.Listbox(frame, height=6, width=70)
    listbox_resultados.pack(pady=5)

    codigos_memoria = []

    def buscar():
        query = entry_query.get().strip().lower()
        listbox_resultados.delete(0, tk.END)
        codigos_memoria.clear()

        if query == "" or query == placeholder.lower():
            messagebox.showwarning("Atención", "Por favor escribe una comuna válida.")
            return

        comuna_col = next((col for col in df_codigos.columns if "comuna" in col.lower()), None)
        region_col = next((col for col in df_codigos.columns if "región" in col.lower() or "region" in col.lower()), None)
        codigo_col = next((col for col in df_codigos.columns if "código" in col.lower() or "codigo" in col.lower()), None)

        if not comuna_col or not codigo_col:
            messagebox.showerror("Error", "El archivo no tiene columnas 'Comuna' y 'Código'.")
            return

        df_filtrado = df_codigos[df_codigos[comuna_col].str.lower() == query]

        if df_filtrado.empty:
            listbox_resultados.insert(tk.END, "Comuna no encontrada.")
            return

        for _, row in df_filtrado.iterrows():
            comuna = row[comuna_col]
            codigo = str(row[codigo_col])
            region = row.get(region_col, "-") if region_col else "-"
            texto = f"{region} - {comuna} | Código: {codigo}"
            listbox_resultados.insert(tk.END, texto)
            codigos_memoria.append(codigo)

    def copiar_codigo():
        seleccion = listbox_resultados.curselection()
        if not seleccion or not codigos_memoria:
            messagebox.showinfo("Selecciona una comuna", "Debes buscar y seleccionar una comuna.")
            return
        idx = seleccion[0]
        codigo = codigos_memoria[idx]
        parent.clipboard_clear()
        parent.clipboard_append(codigo)
        parent.update()
        messagebox.showinfo("Copiado", f"Código postal '{codigo}' copiado al portapapeles.")

    tk.Button(frame, text="Buscar", command=buscar).pack(pady=5)
    tk.Button(frame, text="Copiar código", command=copiar_codigo).pack(pady=5)
