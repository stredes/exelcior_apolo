import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from app.utils.logger_setup import log_evento 

def abrir_visor_logs(parent=None):
    log_dir = Path("logs")
    if not log_dir.exists():
        messagebox.showinfo("Logs", "No hay logs disponibles.")
        return

    archivos = sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not archivos:
        messagebox.showinfo("Logs", "No se encontraron archivos de log.")
        return

    visor = tk.Toplevel(parent)
    visor.title("Visor de Logs")
    visor.geometry("900x600")
    visor.configure(bg="#F9FAFB")

    frame_selector = ttk.Frame(visor)
    frame_selector.pack(fill="x", padx=10, pady=10)

    ttk.Label(frame_selector, text="Seleccionar archivo de log:").pack(side="left")

    archivo_var = tk.StringVar()
    archivo_var.set(archivos[0].name)

    combo = ttk.Combobox(frame_selector, textvariable=archivo_var, values=[a.name for a in archivos], state="readonly")
    combo.pack(side="left", padx=10, fill="x", expand=True)

    frame_texto = ttk.Frame(visor)
    frame_texto.pack(fill="both", expand=True, padx=10, pady=5)

    scrollbar = tk.Scrollbar(frame_texto)
    scrollbar.pack(side="right", fill="y")

    texto = tk.Text(frame_texto, yscrollcommand=scrollbar.set, wrap="none", font=("Courier", 10))
    texto.pack(fill="both", expand=True)
    scrollbar.config(command=texto.yview)

    def cargar_log(*args):
        ruta = log_dir / archivo_var.get()
        if ruta.exists():
            with ruta.open("r", encoding="utf-8", errors="ignore") as f:
                texto.delete("1.0", tk.END)
                texto.insert(tk.END, f.read())

    combo.bind("<<ComboboxSelected>>", cargar_log)
    cargar_log()

    ttk.Button(visor, text="Cerrar", command=visor.destroy).pack(pady=5)

    log_evento("Visor de logs abierto desde la interfaz", "info")

