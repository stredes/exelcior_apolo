import pandas as pd
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import difflib
import json

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "user_config.json"

def cargar_configuracion():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_configuracion(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def cargar_codigos_postales():
    config = cargar_configuracion()
    ruta = config.get("ruta_postales")

    if ruta and Path(ruta).exists():
        df = pd.read_excel(ruta)
    else:
        ruta_manual = filedialog.askopenfilename(title="Selecciona el archivo 'Codigos Postales SAM.xlsx'")
        if not ruta_manual:
            messagebox.showerror("Error", "Archivo de códigos postales no seleccionado.")
            return pd.DataFrame()
        df = pd.read_excel(ruta_manual)
        config["ruta_postales"] = ruta_manual
        guardar_configuracion(config)

    df.columns = [c.lower().strip() for c in df.columns]
    return df

def buscar_codigos_postales(df, comuna_input):
    comuna_col = next((c for c in df.columns if "comuna" in c), None)
    codigo_col = next((c for c in df.columns if "codigo" in c or "código" in c), None)

    if not comuna_col or not codigo_col:
        return []

    comunas_unicas = df[comuna_col].dropna().astype(str).str.lower().unique()
    aproximadas = difflib.get_close_matches(comuna_input.lower(), comunas_unicas, n=5, cutoff=0.5)

    resultados = []
    for comuna in aproximadas:
        rows = df[df[comuna_col].str.lower() == comuna]
        for _, r in rows.iterrows():
            resultados.append((r[comuna_col], r[codigo_col]))
    return resultados

def crear_widget_postal(parent):
    df = cargar_codigos_postales()

    frame = tk.LabelFrame(parent, text="📦 Buscar Código Postal", padx=10, pady=10)
    frame.pack(padx=10, pady=10, fill="x")

    entry = tk.Entry(frame, width=40, fg="gray")
    placeholder = "Ej: Chillán"
    entry.insert(0, placeholder)
    entry.pack()

    listbox = tk.Listbox(frame, width=60, height=6)
    listbox.pack(pady=5)

    codigos_en_memoria = []

    def on_focus_in(e):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg="black")

    def on_focus_out(e):
        if entry.get() == "":
            entry.insert(0, placeholder)
            entry.config(fg="gray")

    def buscar():
        query = entry.get().strip()
        listbox.delete(0, tk.END)
        codigos_en_memoria.clear()

        if not query or query == placeholder:
            return

        resultados = buscar_codigos_postales(df, query)
        if not resultados:
            listbox.insert(tk.END, "No se encontró el código postal.")
            return

        for comuna, codigo in resultados:
            listbox.insert(tk.END, f"{comuna} | Código: {codigo}")
            codigos_en_memoria.append(str(codigo))

    def copiar_codigo():
        idx = listbox.curselection()
        if not idx:
            return
        codigo = codigos_en_memoria[idx[0]]
        parent.clipboard_clear()
        parent.clipboard_append(codigo)
        parent.update()
        messagebox.showinfo("Copiado", f"Código {codigo} copiado al portapapeles.")

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

    tk.Button(frame, text="Buscar", command=buscar).pack(pady=2)
    tk.Button(frame, text="Copiar código", command=copiar_codigo).pack(pady=2)
