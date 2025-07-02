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

# Configuración
DEFAULT_PRINTER_NAME = "URBANO"  # Puedes cargar esto desde un archivo de config

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

def imprimir_pdf(path_pdf: Path, printer_name: str = DEFAULT_PRINTER_NAME):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(str(path_pdf), "print")
        elif system == "Linux":
            os.system(f"lp '{path_pdf}'")
        else:
            raise NotImplementedError(f"Plataforma no compatible: {system}")
    except Exception as e:
        messagebox.showerror("Error al imprimir", f"No se pudo imprimir el PDF:\n{e}")

def crear_editor_etiqueta(df_clientes, parent=None):
    ventana = tk.Toplevel(parent)
    ventana.title("Editor de Etiquetas 10x10 cm")
    ventana.geometry("400x500")

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

    def cargar_datos_cliente(event=None):
        rut = entradas["rut"].get()
        cliente = buscar_cliente_por_rut(df_clientes, rut)
        if cliente:
            entradas["razsoc"].delete(0, tk.END)
            entradas["razsoc"].insert(0, cliente["razsoc"])
            entradas["dir"].delete(0, tk.END)
            entradas["dir"].insert(0, cliente["dir"])
            entradas["comuna"].delete(0, tk.END)
            entradas["comuna"].insert(0, cliente["comuna"])
            entradas["ciudad"].delete(0, tk.END)
            entradas["ciudad"].insert(0, cliente["ciudad"])
        else:
            messagebox.showerror("RUT no encontrado", "No se encontró el cliente para el RUT ingresado.")

    entradas["rut"].bind("<Return>", cargar_datos_cliente)

    def generar_y_imprimir():
        try:
            data = {k: v.get() for k, v in entradas.items()}
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                output_path = Path(temp_pdf.name)
            generar_etiqueta_pdf(data, output_path)
            imprimir_pdf(output_path)
            output_path.unlink(missing_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar o imprimir la etiqueta:\n{e}")

    ttk.Button(frame, text="Imprimir Etiqueta", command=generar_y_imprimir).grid(
        row=len(campos), column=0, columnspan=2, pady=15
    )
