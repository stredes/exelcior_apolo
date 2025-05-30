# main_app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

from app.config.config_dialog import ConfigDialog
from app.core.excel_processor import validate_file, load_excel, apply_transformation
from app.printer.exporter import export_to_pdf
from app.core.herramientas import abrir_herramientas
from app.db.database import init_db, save_file_history
from app.core.autoloader import find_latest_file_by_mode, set_carpeta_descarga_personalizada
from app.core.logger_eventos import capturar_log_bod1
from app.utils.utils import load_config
from app.gui.etiqueta_editor import crear_editor_etiqueta, cargar_clientes
from app.gui.sra_mary import SraMaryView
from app.gui.inventario_view import InventarioView
from app.printer import (
    printer_fedex,
    printer_urbano,
    printer_listados,
    printer_etiquetas
)


class ExcelPrinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transformador Excel - Dashboard")
        self.geometry("750x700")
        self.configure(bg="#F9FAFB")

        init_db()
        self.df = None
        self.transformed_df = None
        self.mode = "listados"
        self.processing = False
        self.config_columns = load_config()
        self.mode_vars = {m: tk.BooleanVar(value=(m == "listados")) for m in ["urbano", "fedex", "listados"]}

        self._setup_styles()
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_status_bar()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TButton", font=("Segoe UI", 11), padding=8)
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TCheckbutton", font=("Segoe UI", 11))

    def _setup_sidebar(self):
        sidebar = tk.Frame(self, bg="#111827", width=200)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="Menú", bg="#111827", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(pady=20)

        buttons = [
            ("Seleccionar Excel 📂", self._threaded_select_file),
            ("Carga Automática 🚀", self._threaded_auto_load),
            ("Configuración ⚙️", self._open_config_menu),
            ("Exportar PDF 📄", lambda: export_to_pdf(self.transformed_df, self)),
            ("Ver Logs 📋", self._view_logs),
            ("Herramientas 🛠️", lambda: abrir_herramientas(self, self.transformed_df)),
            ("Etiquetas 🏷️", self._abrir_editor_etiquetas),
            ("Buscar Códigos Postales 🧭", self._abrir_buscador_codigos_postales),
            ("Sra Mary 👩‍💼", self._abrir_sra_mary),
            ("Inventario 📦", lambda: InventarioView(self)),
        ]

        for text, command in buttons:
            ttk.Button(sidebar, text=text, command=command).pack(pady=10, fill="x", padx=10)

        ttk.Button(sidebar, text="Acerca de 💼", command=self._mostrar_acerca_de).pack(pady=10, fill="x", padx=10)
        ttk.Button(sidebar, text="Salir ❌", command=self.quit).pack(side="bottom", pady=20, fill="x", padx=10)

    def _setup_main_area(self):
        self.main_frame = tk.Frame(self, bg="#F9FAFB")
        self.main_frame.pack(side="left", fill="both", expand=True)

        tk.Label(self.main_frame, text="Transformador Excel",
                 bg="#F9FAFB", fg="#111827", font=("Segoe UI", 18, "bold")).pack(pady=20)

        mode_frame = ttk.LabelFrame(self.main_frame, text="Modo de Operación", padding=15)
        mode_frame.pack(pady=10)

        for m in self.mode_vars:
            ttk.Checkbutton(mode_frame, text=m.capitalize(),
                            variable=self.mode_vars[m],
                            command=lambda m=m: self._update_mode(m)).pack(side=tk.LEFT, padx=10)

    def _setup_status_bar(self):
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var,
                  relief=tk.SUNKEN, anchor=tk.W, padding=5).pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, message: str):
        self.status_var.set(message)

    def _update_mode(self, selected_mode: str):
        for mode in self.mode_vars:
            self.mode_vars[mode].set(mode == selected_mode)
        self.mode = selected_mode

    def _abrir_buscador_codigos_postales(self):
        from app.gui.buscador_codigos_postales import BuscadorCodigosPostales
        BuscadorCodigosPostales(self)

    def _abrir_sra_mary(self):
        SraMaryView(self)

    def _mostrar_acerca_de(self):
        messagebox.showinfo("Acerca de", "Exelcior Apolo\n\nSistema integral de impresión, logística y trazabilidad para operaciones clínicas, desarrollado por Gian Lucas y GCNJ.\n\nVersión 2025 — Funciona en Windows y Linux.")

    def _threaded_select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file_path and validate_file(file_path):
            set_carpeta_descarga_personalizada(Path(file_path).parent, self.mode)
            self.processing = True
            threading.Thread(target=self._process_file, args=(file_path,), daemon=True).start()

    def _threaded_auto_load(self):
        if self.processing:
            return
        threading.Thread(target=self._auto_load_latest_file, daemon=True).start()

    def _auto_load_latest_file(self):
        self._update_status("Buscando archivo más reciente...")
        try:
            archivo, estado = find_latest_file_by_mode(self.mode)
            if estado == "ok" and archivo and validate_file(str(archivo)):
                self._update_status(f"✅ Cargado: {archivo.name}")
                self._process_file(str(archivo))
            elif estado == "no_match":
                self._update_status("⚠️ No se encontraron archivos compatibles.")
                messagebox.showwarning("Sin coincidencias", f"No hay archivos válidos para el modo '{self.mode}'.")
            elif estado == "empty_folder":
                self._update_status("📂 Carpeta vacía o inexistente.")
                messagebox.showerror("Carpeta vacía", "La carpeta de descargas está vacía o no existe.")
            else:
                self._update_status("❌ Error en la autocarga.")
        except Exception as e:
            logging.error(f"Error en carga automática: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.processing = False

    def _process_file(self, file_path: str):
        self.after(0, lambda: self._update_status("Procesando archivo..."))
        capturar_log_bod1(f"Iniciando procesamiento: {file_path}", "info")
        try:
            df = load_excel(file_path, self.config_columns, self.mode)
            self.df = df
            self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)
            save_file_history(file_path, self.mode)
            self.after(0, self._show_preview)
        except Exception as e:
            logging.error(f"Error procesando archivo: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"No se pudo procesar el archivo:\n{e}"))
        finally:
            self.processing = False
            self.after(0, lambda: self._update_status("Listo"))

    def _show_preview(self):
        if self.transformed_df is None or self.transformed_df.empty:
            messagebox.showerror("Error", "No hay datos para mostrar.")
            return

        preview_win = tk.Toplevel(self)
        preview_win.title("Vista Previa")
        preview_win.geometry("950x600")
        preview_win.configure(bg="#F9FAFB")

        tree_frame = ttk.Frame(preview_win, padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = list(self.transformed_df.columns)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, minwidth=80, anchor=tk.CENTER)

        for row in self.transformed_df.itertuples(index=False):
            tree.insert("", "end", values=row)

        ttk.Button(preview_win, text="Imprimir", command=self._threaded_print).pack(pady=5)

    def _threaded_print(self):
        if self.processing or self.transformed_df is None:
            messagebox.showerror("Error", "Primero debe cargar un archivo Excel válido.")
            return
        threading.Thread(target=self._print_document, daemon=True).start()

    def _print_document(self):
        try:
            printer_map = {
                "fedex": printer_fedex.print_fedex,
                "urbano": printer_urbano.print_urbano,
                "listados": printer_listados.print_listados,
                "etiquetas": printer_etiquetas.print_etiquetas,
            }

            print_func = printer_map.get(self.mode)
            if not print_func:
                raise ValueError(f"No se encontró printer para el modo: {self.mode}")

            print_func(None, self.config_columns, self.transformed_df)
        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir:\n{e}")
            logging.error(f"Error en impresión: {e}")
            capturar_log_bod1(f"Error durante impresión: {e}", "error")

    def _open_config_menu(self):
        if self.df is None:
            messagebox.showerror("Error", "Primero cargue un archivo Excel.")
            return
        self.open_config_dialog(self.mode)

    def open_config_dialog(self, mode: str):
        dialog = ConfigDialog(self, mode, list(self.df.columns), self.config_columns)
        self.wait_window(dialog)
        self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

    def _abrir_editor_etiquetas(self):
        try:
            path = filedialog.askopenfilename(
                title="Selecciona el archivo de etiquetas",
                filetypes=[("Excel Files", "*.xlsx")]
            )
            if not path:
                return
            df_clientes = cargar_clientes(path)
            crear_editor_etiqueta(df_clientes)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el editor de etiquetas:\n{e}")

    def _view_logs(self):
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        if not log_dir.exists():
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return

        log_files = sorted(log_dir.glob("*.log"), reverse=True)
        if not log_files:
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return

        latest_log = log_files[0]

        log_win = tk.Toplevel(self)
        log_win.title(f"Visor de Logs - {latest_log.name}")
        log_win.geometry("1000x600")
        log_win.configure(bg="#F9FAFB")

        frame = ttk.Frame(log_win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(frame, wrap="word", font=("Consolas", 10), bg="white")
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, command=txt.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        txt.config(yscrollcommand=scrollbar.set)

        txt.tag_configure("ERROR", foreground="red")
        txt.tag_configure("WARNING", foreground="orange")
        txt.tag_configure("DEBUG", foreground="gray")
        txt.tag_configure("INFO", foreground="black")

        def cargar_log():
            txt.config(state="normal")
            txt.delete("1.0", tk.END)
            with latest_log.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "ERROR" in line:
                        txt.insert(tk.END, line, "ERROR")
                    elif "WARNING" in line:
                        txt.insert(tk.END, line, "WARNING")
                    elif "DEBUG" in line:
                        txt.insert(tk.END, line, "DEBUG")
                    else:
                        txt.insert(tk.END, line, "INFO")
            txt.config(state="disabled")

        ttk.Button(log_win, text="🔁 Refrescar Log", command=cargar_log).pack(pady=5)
        cargar_log()


def main():
    app = ExcelPrinterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
