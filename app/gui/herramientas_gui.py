import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
import os
import pandas as pd

from app.core import herramientas as core


def abrir_herramientas(parent, df: pd.DataFrame):
    if df is None or df.empty:
        messagebox.showerror("Error", "No hay datos disponibles.")
        return

    tools_win = tk.Toplevel(parent)
    tools_win.title("Herramientas Avanzadas")
    tools_win.geometry("400x550")
    style = ttk.Style()
    style.configure("TButton", font=("Segoe UI", 11), padding=8)

    # ========== FUNCIONES AUXILIARES DE GUI ==========

    def gui_mostrar_estadisticas():
        try:
            est = core.obtener_estadisticas(df)
            texto = (
                f"📊 Total de filas: {est['filas']}\n"
                f"📊 Total de columnas: {est['columnas']}\n"
                f"📦 BULTOS: {est['bultos']}\n"
                f"👥 Clientes únicos: {est['clientes_unicos']}\n"
                f"📅 Fechas de envío: {est['fechas_envio']}"
            )
            messagebox.showinfo("Estadísticas del Excel", texto)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def gui_exportar_csv():
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            try:
                core.exportar_csv_a_path(df, Path(path))
                messagebox.showinfo("Exportación", f"Archivo exportado: {path}")
            except Exception as e:
                messagebox.showerror("Error al exportar", str(e))

    def gui_exportar_xlsx():
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            try:
                core.exportar_xlsx_a_path(df, Path(path))
                messagebox.showinfo("Exportación", f"Archivo exportado: {path}")
            except Exception as e:
                messagebox.showerror("Error al exportar", str(e))

    def gui_exportar_pdf():
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            try:
                core.exportar_pdf_a_path(df, Path(path))
                messagebox.showinfo("Exportación", f"Archivo exportado: {path}")
            except Exception as e:
                messagebox.showerror("Error al exportar", str(e))

    def gui_editor_columnas():
        editor = tk.Toplevel(tools_win)
        editor.title("Editor de Columnas")
        editor.geometry("400x500")

        columnas = list(df.columns)
        seleccionadas = {col: tk.BooleanVar(value=True) for col in columnas}
        nuevos_nombres = {}

        canvas_frame = tk.Canvas(editor)
        scroll = ttk.Scrollbar(editor, orient="vertical", command=canvas_frame.yview)
        frame = tk.Frame(canvas_frame)
        frame.bind("<Configure>", lambda e: canvas_frame.configure(scrollregion=canvas_frame.bbox("all")))
        canvas_frame.create_window((0, 0), window=frame, anchor="nw")
        canvas_frame.configure(yscrollcommand=scroll.set)
        canvas_frame.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for col in columnas:
            chk = tk.Checkbutton(frame, text=col, variable=seleccionadas[col])
            chk.pack(anchor="w", padx=5)
            entry = tk.Entry(frame)
            entry.insert(0, col)
            entry.pack(fill="x", padx=10, pady=2)
            nuevos_nombres[col] = entry

        def aplicar():
            try:
                columnas_a_mantener = [col for col in columnas if seleccionadas[col].get()]
                nuevos = {col: nuevos_nombres[col].get() for col in columnas_a_mantener if nuevos_nombres[col].get() != col}
                nuevo_df = core.aplicar_edicion_columnas(df.copy(), columnas_a_mantener, nuevos)
                df.clear()
                df.update(nuevo_df)
                messagebox.showinfo("Editor", "Cambios aplicados.")
                editor.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(editor, text="Aplicar", command=aplicar).pack(pady=10)

    def gui_buscar_datos():
        buscar_win = tk.Toplevel(tools_win)
        buscar_win.title("Buscar en Excel")
        buscar_win.geometry("300x160")

        tk.Label(buscar_win, text="Columna:").pack(pady=5)
        combo = ttk.Combobox(buscar_win, values=list(df.columns))
        combo.pack(pady=5)
        combo.current(0)

        tk.Label(buscar_win, text="Buscar:").pack(pady=5)
        entry = tk.Entry(buscar_win)
        entry.pack(pady=5)
        entry.focus()

        def buscar():
            try:
                col = combo.get()
                val = entry.get()
                resultado = core.buscar_por_columna(df, col, val)
                if resultado.empty:
                    messagebox.showinfo("Búsqueda", "No se encontraron resultados.")
                else:
                    stats = core.obtener_estadisticas(resultado)
                    texto = (
                        f"📊 Resultados: {len(resultado)} filas\n"
                        f"👥 Clientes únicos: {stats['clientes_unicos']}\n"
                        f"📦 BULTOS: {stats['bultos']}"
                    )
                    messagebox.showinfo("Resultados", texto)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(buscar_win, text="Buscar", command=buscar).pack(pady=10)

    def gui_enviar_email():
        try:
            smtp_server = os.getenv("SMTP_SERVER", "smtp.tudominio.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))

            remitente = simpledialog.askstring("Email", "Correo remitente:")
            if not remitente:
                return

            password = simpledialog.askstring("Contraseña", f"Contraseña de {remitente}:", show='*')
            if not password:
                return

            destinatario = simpledialog.askstring("Destinatario", "Correo destino:")
            if not destinatario:
                return

            core.enviar_dataframe_por_email(df, remitente, password, destinatario, smtp_server, smtp_port)
            messagebox.showinfo("Email", "Correo enviado correctamente.")
        except Exception as e:
            messagebox.showerror("Error al enviar", str(e))

    # ========== BOTONES DE FUNCIONALIDADES ==========
    ttk.Button(tools_win, text="📊 Ver Estadísticas", command=gui_mostrar_estadisticas).pack(pady=10, fill="x", padx=20)
    ttk.Button(tools_win, text="📁 Exportar CSV", command=gui_exportar_csv).pack(pady=10, fill="x", padx=20)
    ttk.Button(tools_win, text="📁 Exportar XLSX", command=gui_exportar_xlsx).pack(pady=10, fill="x", padx=20)
    ttk.Button(tools_win, text="📁 Exportar PDF", command=gui_exportar_pdf).pack(pady=10, fill="x", padx=20)
    ttk.Button(tools_win, text="🎨 Editor Columnas", command=gui_editor_columnas).pack(pady=10, fill="x", padx=20)
    ttk.Button(tools_win, text="🔍 Buscar Datos", command=gui_buscar_datos).pack(pady=10, fill="x", padx=20)
    ttk.Button(tools_win, text="📧 Enviar Email", command=gui_enviar_email).pack(pady=10, fill="x", padx=20)

    # ========== ACCESIBILIDAD ==========
    tools_win.bind("<Escape>", lambda e: tools_win.destroy())
