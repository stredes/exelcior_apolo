import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
import pandas as pd
from pathlib import Path
from datetime import datetime

# Cargar datos de clientes desde Excel
def cargar_clientes(path_excel):
    xls = pd.ExcelFile(path_excel)
    df_clientes = xls.parse("Clientes")
    return df_clientes

# Buscar cliente por RUT
def buscar_cliente_por_rut(df_clientes, rut):
    fila = df_clientes[df_clientes['rut'] == rut.strip()]
    if not fila.empty:
        datos = fila.iloc[0]
        return {
            "razsoc": datos.get("razsoc", ""),
            "dir": datos.get("dir", ""),
            "comuna": datos.get("comuna", ""),
            "ciudad": datos.get("ciudad", "")
        }
    return None

# Generar etiqueta PDF con tamaño configurable
def generar_etiqueta_pdf(data, output_path, width_cm=10, height_cm=10):
    c = canvas.Canvas(str(output_path), pagesize=(width_cm*cm, height_cm*cm))
    c.setFont("Helvetica", 10)

    y = (height_cm - 0.5) * cm
    row_height = 1.3 * cm

    for key, label in [
        ("guia", "Guía"),
        ("rut", "RUT"),
        ("razsoc", "Cliente"),
        ("dir", "Dirección"),
        ("comuna", "Comuna"),
        ("ciudad", "Ciudad"),
        ("bultos", "Bultos"),
        ("transporte", "Transporte")
    ]:
        valor = data.get(key, "")
        c.rect(0.5*cm, y - row_height + 0.3*cm, (width_cm - 1)*cm, row_height, stroke=1, fill=0)
        c.drawString(0.7*cm, y, f"{label}: {valor}")
        y -= row_height

    c.save()

# Interfaz Tkinter
def crear_editor_etiqueta(df_clientes):
    root = tk.Tk()
    root.title("Editor de Etiquetas")

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0)

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
        ttk.Label(frame, text=label + ":").grid(row=idx, column=0, sticky="e", pady=5)
        entry = ttk.Entry(frame, width=40)
        entry.grid(row=idx, column=1, pady=5)
        entradas[key] = entry

    # Tamaño de etiqueta
    ttk.Label(frame, text="Ancho (cm):").grid(row=len(campos), column=0, sticky="e", pady=5)
    ancho_entry = ttk.Entry(frame, width=10)
    ancho_entry.insert(0, "10")
    ancho_entry.grid(row=len(campos), column=1, sticky="w", pady=5)

    ttk.Label(frame, text="Alto (cm):").grid(row=len(campos)+1, column=0, sticky="e", pady=5)
    alto_entry = ttk.Entry(frame, width=10)
    alto_entry.insert(0, "10")
    alto_entry.grid(row=len(campos)+1, column=1, sticky="w", pady=5)

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

    def generar_pdf():
        data = {k: v.get() for k, v in entradas.items()}
        try:
            width_cm = float(ancho_entry.get())
            height_cm = float(alto_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Tamaño de etiqueta inválido.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path.cwd() / f"etiqueta_{data['rut']}_{timestamp}.pdf"
        generar_etiqueta_pdf(data, output_path, width_cm, height_cm)
        messagebox.showinfo("Etiqueta generada", f"Etiqueta guardada en:\n{output_path}")

    ttk.Button(frame, text="Generar Etiqueta PDF", command=generar_pdf).grid(row=len(campos)+2, column=0, columnspan=2, pady=15)

    root.mainloop()

# --- Carga inicial ---
if __name__ == "__main__":
    excel_path = "etiqueta pedido.xlsx"  # Debe estar en el mismo directorio
    df_clientes = cargar_clientes(excel_path)
    crear_editor_etiqueta(df_clientes)