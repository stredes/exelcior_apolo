import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import pandas as pd
import tempfile
import os
import platform
import json

# Ruta al archivo de configuración
CONFIG_PATH = Path("app/config/excel_printer_config.json")

def cargar_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def cargar_clientes(path_excel):
    df_clientes = pd.read_excel(path_excel, sheet_name="Clientes")
    return df_clientes

def buscar_cliente_por_rut(df_clientes, rut):
    fila = df_clientes[df_clientes['rut'].astype(str).str.strip() == rut.strip()]
    if not fila.empty:
        datos = fila.iloc[0]
        return {
            "razsoc": datos.get("razsoc", ""),
            "dir": datos.get("dir", ""),
            "comuna": datos.get("comuna", ""),
            "ciudad": datos.get("ciudad", "")
        }
    return None

def generar_etiqueta_pdf(data, output_path: Path):
    c = canvas.Canvas(str(output_path), pagesize=(10 * cm, 10 * cm))
    c.setFont("Helvetica", 10)
    y = 9.5 * cm
    row_height = 1.3 * cm

    campos = [
        ("guia", "Guía"),
        ("rut", "RUT"),
        ("razsoc", "Cliente"),
        ("dir", "Dirección"),
        ("comuna", "Comuna"),
        ("ciudad", "Ciudad"),
        ("bultos", "Bultos"),
        ("transporte", "Transporte")
    ]

    for key, label in campos:
        valor = data.get(key, "")
        c.rect(0.5 * cm, y - row_height + 0.3 * cm, 9 * cm, row_height, stroke=1, fill=0)
        c.drawString(0.7 * cm, y, f"{label}: {valor}")
        y -= row_height

    c.save()

def imprimir_pdf(path_pdf: Path, printer_name: str):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(str(path_pdf), "print")
        elif system == "Linux":
            os.system(f"lp -d '{printer_name}' '{path_pdf}'")
        else:
            raise NotImplementedError(f"Plataforma no compatible: {system}")
    except Exception as e:
        messagebox.showerror("Error al imprimir", f"No se pudo imprimir el PDF:\n{e}")

def crear_editor_etiqueta(df_clientes, parent=None):
    config = cargar_config()
    printer_name_default = config.get("printer_name", "URBANO")

    ventana = tk.Toplevel(parent)
    ventana.title("Editor de Etiquetas 10x10 cm")
    ventana.geometry("400x550")

    frame = ttk.Frame(ventana, padding=20)
    frame.pack(fill="both", expand=True)

    campos = {
        "rut": "RUT",
        "razsoc": "Cliente",
        "dir": "Dirección",
        "comuna": "Comuna",
        "ciudad": "Ciudad",
        "guia": "Guía",
        "bultos": "Bultos",
        "transporte": "Transporte"
    }

    entradas = {}

    for idx, (key, label) in enumerate(campos.items()):
        ttk.Label(frame, text=label + ":").grid(row=idx, column=0, sticky="e", pady=4)
        entry = ttk.Entry(frame, width=35)
        entry.grid(row=idx, column=1, pady=4)
        entradas[key] = entry

    ttk.Label(frame, text="Impresora:").grid(row=len(campos), column=0, sticky="e", pady=4)
    entrada_impresora = ttk.Entry(frame, width=35)
    entrada_impresora.insert(0, printer_name_default)
    entrada_impresora.grid(row=len(campos), column=1, pady=4)

    def cargar_datos_cliente(event=None):
        rut = entradas["rut"].get()
        cliente = buscar_cliente_por_rut(df_clientes, rut)
        if cliente:
            for campo in ["razsoc", "dir", "comuna", "ciudad"]:
                entradas[campo].delete(0, tk.END)
                entradas[campo].insert(0, cliente[campo])
        else:
            messagebox.showerror("RUT no encontrado", "No se encontró el cliente para el RUT ingresado.")

    entradas["rut"].bind("<Return>", cargar_datos_cliente)

    def generar_y_imprimir():
        try:
            data = {k: v.get() for k, v in entradas.items()}
            printer_name = entrada_impresora.get().strip()
            config["printer_name"] = printer_name
            guardar_config(config)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                output_path = Path(temp_pdf.name)

            generar_etiqueta_pdf(data, output_path)
            imprimir_pdf(output_path, printer_name)
            output_path.unlink(missing_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar o imprimir la etiqueta:\n{e}")

    ttk.Button(frame, text="Imprimir Etiqueta", command=generar_y_imprimir).grid(
        row=len(campos) + 1, column=0, columnspan=2, pady=15
    )
