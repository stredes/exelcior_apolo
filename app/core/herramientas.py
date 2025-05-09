import json
import os
import smtplib
import tempfile
import tkinter as tk
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import pandas as pd

# ---------- Configuración de Usuario (almacenamiento) ----------
USER_CONFIG_FILE = Path("config_usuario.json")


def cargar_config_usuario():
    if USER_CONFIG_FILE.exists():
        with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_config_usuario(config):
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# ---------- Estadísticas Dinámicas ----------
def mostrar_estadisticas(df):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para mostrar estadísticas.")
        return

    total_filas, total_columnas = df.shape
    suma_bultos = df["BULTOS"].sum() if "BULTOS" in df.columns else "N/A"
    clientes_unicos = df["Cliente"].nunique() if "Cliente" in df.columns else "N/A"
    fechas_envio = df["Fecha"].dropna().unique() if "Fecha" in df.columns else "N/A"

    estadisticas = (
        f"📊 Total de filas: {total_filas}\n"
        f"📊 Total de columnas: {total_columnas}\n"
        f"📦 Sumatoria de BULTOS: {suma_bultos}\n"
        f"👥 Clientes únicos: {clientes_unicos}\n"
        f"📅 Fechas de envío: {fechas_envio}"
    )

    messagebox.showinfo("Estadísticas del Excel", estadisticas)


# ---------- Exportaciones ----------
def exportar_csv(df):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para exportar.")
        return
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv", filetypes=[("CSV files", "*.csv")]
    )
    if file_path:
        df.to_csv(file_path, index=False)
        messagebox.showinfo("Exportar CSV", f"Archivo exportado: {file_path}")


def exportar_xlsx(df):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para exportar.")
        return
    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")]
    )
    if file_path:
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Exportar XLSX", f"Archivo exportado: {file_path}")


def exportar_pdf(df):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para exportar.")
        return

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
    )
    if file_path:
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter
        y = height - 40
        c.setFont("Helvetica", 10)
        for col in df.columns:
            c.drawString(30, y, col)
            y -= 15
        y -= 10
        for idx, row in df.head(50).iterrows():
            line = ", ".join(str(val) for val in row)
            c.drawString(30, y, line)
            y -= 15
            if y < 40:
                c.showPage()
                y = height - 40
        c.save()
        messagebox.showinfo("Exportar PDF", f"Archivo exportado: {file_path}")


# ---------- Editor Visual de Columnas ----------
def editor_columnas(df, update_callback=None):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para editar.")
        return

    editor = tk.Toplevel()
    editor.title("Editor de Columnas")
    editor.geometry("400x500")

    columnas = list(df.columns)
    seleccionadas = {col: tk.BooleanVar(value=True) for col in columnas}
    nuevos_nombres = {}

    canvas_frame = tk.Canvas(editor)
    scroll = ttk.Scrollbar(editor, orient="vertical", command=canvas_frame.yview)
    frame = tk.Frame(canvas_frame)
    frame.bind(
        "<Configure>",
        lambda e: canvas_frame.configure(scrollregion=canvas_frame.bbox("all")),
    )
    canvas_frame.create_window((0, 0), window=frame, anchor="nw")
    canvas_frame.configure(yscrollcommand=scroll.set)
    canvas_frame.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    for col in columnas:
        chk = tk.Checkbutton(frame, text=col, variable=seleccionadas[col])
        chk.pack(anchor="w")
        entry = tk.Entry(frame)
        entry.insert(0, col)
        entry.pack(fill="x", padx=10)
        nuevos_nombres[col] = entry

    def aplicar():
        columnas_a_eliminar = [col for col in columnas if not seleccionadas[col].get()]
        df.drop(columns=columnas_a_eliminar, inplace=True)
        rename_map = {
            col: nuevos_nombres[col].get()
            for col in columnas
            if col != nuevos_nombres[col].get()
        }
        df.rename(columns=rename_map, inplace=True)
        if update_callback:
            update_callback()
        messagebox.showinfo("Editor", "Cambios aplicados.")
        editor.destroy()

    tk.Button(editor, text="Aplicar", command=aplicar).pack(pady=10)


# ---------- Búsqueda ----------
def buscar_datos(df, parent):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para buscar.")
        return

    def buscar():
        criterio = combo.get()
        valor = entry.get()
        if criterio not in df.columns:
            messagebox.showerror("Error", f"Columna '{criterio}' no encontrada.")
            return
        resultado = df[
            df[criterio].astype(str).str.contains(valor, case=False, na=False)
        ]
        if resultado.empty:
            messagebox.showinfo("Búsqueda", "No se encontraron resultados.")
        else:
            mostrar_estadisticas(resultado)

    buscar_win = tk.Toplevel(parent)
    buscar_win.title("Buscar en Excel")
    buscar_win.geometry("300x150")
    tk.Label(buscar_win, text="Columna:").pack(pady=5)
    combo = ttk.Combobox(buscar_win, values=list(df.columns))
    combo.pack(pady=5)
    combo.current(0)
    tk.Label(buscar_win, text="Buscar:").pack(pady=5)
    entry = tk.Entry(buscar_win)
    entry.pack(pady=5)
    tk.Button(buscar_win, text="Buscar", command=buscar).pack(pady=10)


# ---------- Envío por Email ----------
def enviar_email(df, parent):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos para enviar.")
        return

    config = cargar_config_usuario()
    email_saved = config.get("email", "")
    password_saved = config.get("password", "")

    if not email_saved or not password_saved:
        login_win = tk.Toplevel(parent)
        login_win.title("Login Email")
        login_win.geometry("300x200")

        tk.Label(login_win, text="Correo:").pack(pady=5)
        email_entry = tk.Entry(login_win)
        email_entry.pack(pady=5)
        tk.Label(login_win, text="Contraseña:").pack(pady=5)
        password_entry = tk.Entry(login_win, show="*")
        password_entry.pack(pady=5)

        def guardar():
            email = email_entry.get()
            password = password_entry.get()
            if email and password:
                config["email"] = email
                config["password"] = password
                guardar_config_usuario(config)
                login_win.destroy()

        tk.Button(login_win, text="Guardar", command=guardar).pack(pady=10)
        parent.wait_window(login_win)

    to_email = simpledialog.askstring("Enviar Email", "Correo destino:")
    if not to_email:
        return

    try:
        temp_path = (
            Path(tempfile.gettempdir())
            / f"datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        df.to_excel(temp_path, index=False)

        msg = EmailMessage()
        msg["Subject"] = "Datos Exportados"
        msg["From"] = config["email"]
        msg["To"] = to_email
        msg.set_content("Adjunto los datos solicitados.")
        with open(temp_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=temp_path.name,
            )

        with smtplib.SMTP("smtp.tudominio.com", 587) as server:
            server.starttls()
            server.login(config["email"], config["password"])
            server.send_message(msg)

        messagebox.showinfo("Email", f"Correo enviado a {to_email}")

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo enviar el email:\n{e}")


# ---------- Función Principal ----------
def abrir_herramientas(parent, df):
    tools_win = tk.Toplevel(parent)
    tools_win.title("Herramientas Avanzadas")
    tools_win.geometry("400x550")

    style = ttk.Style()
    style.configure("TButton", font=("Segoe UI", 11), padding=8)

    ttk.Button(
        tools_win, text="📊 Ver Estadísticas", command=lambda: mostrar_estadisticas(df)
    ).pack(pady=10, fill="x", padx=20)
    ttk.Button(
        tools_win, text="📁 Exportar CSV", command=lambda: exportar_csv(df)
    ).pack(pady=10, fill="x", padx=20)
    ttk.Button(
        tools_win, text="📁 Exportar XLSX", command=lambda: exportar_xlsx(df)
    ).pack(pady=10, fill="x", padx=20)
    ttk.Button(
        tools_win, text="📁 Exportar PDF", command=lambda: exportar_pdf(df)
    ).pack(pady=10, fill="x", padx=20)
    ttk.Button(
        tools_win, text="🎨 Editor Columnas", command=lambda: editor_columnas(df)
    ).pack(pady=10, fill="x", padx=20)
    ttk.Button(
        tools_win, text="🔍 Buscar Datos", command=lambda: buscar_datos(df, tools_win)
    ).pack(pady=10, fill="x", padx=20)
    ttk.Button(
        tools_win, text="📧 Enviar Email", command=lambda: enviar_email(df, tools_win)
    ).pack(pady=10, fill="x", padx=20)


import inspect
import logging
import os
from datetime import datetime
from pathlib import Path


def log_evento(mensaje: str, nivel: str = "info"):
    """
    Guarda logs con nombre dinámico según el archivo donde se llama.
    Ejemplo: logs/etiqueta_editor_log_20250411.log
    """

    # Detectar el nombre del archivo que llama a esta función
    frame = inspect.stack()[1]
    archivo_llamador = os.path.splitext(os.path.basename(frame.filename))[0]
    log_name = f"{archivo_llamador}_log_{datetime.now().strftime('%Y%m%d')}"

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{log_name}.log"

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    # Evitar duplicar handlers
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.resolve())
        for h in logger.handlers
    ):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(nivel.lower(), logger.info)(mensaje)
