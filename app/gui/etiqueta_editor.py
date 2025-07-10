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
import subprocess

# Ruta de configuración
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
    return pd.read_excel(path_excel, sheet_name="Clientes")

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

def obtener_impresoras_disponibles():
    system = platform.system()
    impresoras = []
    if system == "Windows":
        try:
            import win32print
            impresoras = [printer[2] for printer in win32print.EnumPrinters(2)]
        except ImportError:
            impresoras = []
    elif system == "Linux":
        try:
            output = subprocess.check_output(["lpstat", "-a"]).decode()
            impresoras = [line.split()[0] for line in output.strip().split("\n") if line]
        except Exception:
            impresoras = []
    return impresoras

def crear_editor_etiqueta(df_clientes, parent=None):
    config = cargar_config()
    printer_name_default = config.get("printer_name", "")

    ventana = tk.Toplevel(parent)
    ventana.title("Editor de Etiquetas 10x10 cm")
    ventana.geometry("420x580")
    ventana.resizable(False, False)

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

    # Crear campos de entrada
    for idx, (key, label) in enumerate(campos.items()):
        ttk.Label(frame, text=label + ":").grid(row=idx, column=0, sticky="e", pady=4)
        entry = ttk.Entry(frame, width=35)
        entry.grid(row=idx, column=1, pady=4)
        entradas[key] = entry

    # Combobox de impresoras
    ttk.Label(frame, text="Impresora:").grid(row=len(campos), column=0, sticky="e", pady=4)
    impresoras = obtener_impresoras_disponibles()
    combo_impresoras = ttk.Combobox(frame, values=impresoras, width=33)
    combo_impresoras.set(printer_name_default)
    combo_impresoras.grid(row=len(campos), column=1, pady=4)

    # Autocompletar cliente al presionar Enter en campo RUT
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

    # Validación de campos obligatorios
    def validar_campos(data):
        obligatorios = ["rut", "razsoc", "dir", "guia", "bultos"]
        faltantes = [campo for campo in obligatorios if not data.get(campo)]
        if faltantes:
            messagebox.showerror("Campos faltantes", "Completa los siguientes campos:\n- " + "\n- ".join(faltantes))
            return False
        return True

    def limpiar_formulario():
        for entry in entradas.values():
            entry.delete(0, tk.END)

    # Generar e imprimir
    def generar_y_imprimir():
        try:
            data = {k: v.get() for k, v in entradas.items()}
            printer_name = combo_impresoras.get().strip()

            if not validar_campos(data):
                return

            config["printer_name"] = printer_name
            guardar_config(config)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                output_path = Path(temp_pdf.name)

            generar_etiqueta_pdf(data, output_path)
            imprimir_pdf(output_path, printer_name)
            output_path.unlink(missing_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar o imprimir la etiqueta:\n{e}")

    # Botones
    ttk.Button(frame, text="Imprimir Etiqueta", command=generar_y_imprimir).grid(
        row=len(campos) + 1, column=0, columnspan=2, pady=10
    )
    ttk.Button(frame, text="Limpiar Formulario", command=limpiar_formulario).grid(
        row=len(campos) + 2, column=0, columnspan=2, pady=5
    )
