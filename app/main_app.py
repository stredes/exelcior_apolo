import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

# Módulos internos
from app.config.config_dialog import ConfigDialog
from app.core.excel_processor import validate_file, load_excel, apply_transformation
from app.printer.exporter import export_to_pdf
from app.gui.herramientas_gui import abrir_herramientas
from app.db.database import init_db, save_file_history, save_print_history
from app.core.autoloader import find_latest_file_by_mode, set_carpeta_descarga_personalizada
from app.core.logger_eventos import capturar_log_bod1
from app.utils.utils import load_config
from app.gui.etiqueta_editor import crear_editor_etiqueta, cargar_clientes
from app.gui.sra_mary import SraMaryView
from app.gui.inventario_view import InventarioView
from app.printer import printer_fedex, printer_urbano, printer_listados, printer_etiquetas


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

        config = load_config()
        self.config_columns = config if isinstance(config, dict) else {}
        self.mode_vars = {m: tk.BooleanVar(value=(m == "listados")) for m in ["urbano", "fedex", "listados"]}

        self._setup_styles()
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_status_bar()

    # ------------------- Setup Estilos y UI -------------------

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TButton", font=("Segoe UI", 11), padding=8)
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TCheckbutton", font=("Segoe UI", 11))

    def _setup_sidebar(self):
        sidebar = tk.Frame(self, bg="#111827", width=200)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="Menú", bg="#111827", fg="white", font=("Segoe UI", 14, "bold")).pack(pady=20)

        botones = [
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

        for texto, accion in botones:
            ttk.Button(sidebar, text=texto, command=accion).pack(pady=10, fill="x", padx=10)

        ttk.Button(sidebar, text="Acerca de 💼", command=self._mostrar_acerca_de).pack(pady=10, fill="x", padx=10)
        ttk.Button(sidebar, text="Salir ❌", command=self.quit).pack(side="bottom", pady=20, fill="x", padx=10)

    def _setup_main_area(self):
        self.main_frame = tk.Frame(self, bg="#F9FAFB")
        self.main_frame.pack(side="left", fill="both", expand=True)

        tk.Label(self.main_frame, text="Transformador Excel", bg="#F9FAFB", fg="#111827",
                 font=("Segoe UI", 18, "bold")).pack(pady=20)

        mode_frame = ttk.LabelFrame(self.main_frame, text="Modo de Operación", padding=15)
        mode_frame.pack(pady=10)

        for modo in self.mode_vars:
            ttk.Checkbutton(mode_frame, text=modo.capitalize(),
                            variable=self.mode_vars[modo],
                            command=lambda m=modo: self._update_mode(m)).pack(side=tk.LEFT, padx=10)

    def _setup_status_bar(self):
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=5).pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------- Funciones UI y navegación -------------------

    def _update_status(self, mensaje: str):
        self.status_var.set(mensaje)

    def _update_mode(self, modo_seleccionado: str):
        for modo in self.mode_vars:
            self.mode_vars[modo].set(modo == modo_seleccionado)
        self.mode = modo_seleccionado

    def _abrir_buscador_codigos_postales(self):
        from app.gui.buscador_codigos_postales import BuscadorCodigosPostales
        BuscadorCodigosPostales(self)

    def _abrir_sra_mary(self):
        SraMaryView(self)

    def _mostrar_acerca_de(self):
        mensaje = (
            "Exelcior Apolo\n\nSistema integral de impresión, logística y trazabilidad "
            "para operaciones clínicas.\n\nDesarrollado por Gian Lucas y GCNJ.\nVersión 2025 — "
            "Funciona en Windows y Linux."
        )
        messagebox.showinfo("Acerca de", mensaje)

    # ------------------- Carga de Archivos -------------------

    def _threaded_select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if path and validate_file(path):
            set_carpeta_descarga_personalizada(Path(path).parent, self.mode)
            self.processing = True
            threading.Thread(target=self._process_file, args=(path,), daemon=True).start()

    def _threaded_auto_load(self):
        if not self.processing:
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
                self.after(0, lambda: messagebox.showwarning("Sin coincidencias", f"No hay archivos válidos para el modo '{self.mode}'"))
            elif estado == "empty_folder":
                self._update_status("📂 Carpeta vacía o inexistente.")
                self.after(0, lambda: messagebox.showerror("Carpeta vacía", "La carpeta de descargas está vacía o no existe."))
            else:
                self._update_status("❌ Error en la autocarga.")
        except Exception as e:
            logging.error(f"Error en carga automática: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.processing = False

    def _process_file(self, path: str):
        self._update_status("Procesando archivo...")
        capturar_log_bod1(f"Iniciando procesamiento: {path}", "info")
        try:
            self.df = load_excel(path, self.config_columns, self.mode)
            self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)
            save_file_history(path, self.mode)
            self.after(0, self._show_preview)
        except Exception as e:
            logging.error(f"Error procesando archivo: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"No se pudo procesar el archivo:\n{e}"))
        finally:
            self.processing = False
            self._update_status("Listo")

    # ------------------- Vista previa e impresión -------------------

    def _show_preview(self):
        if self.transformed_df is None or self.transformed_df.empty:
            messagebox.showerror("Error", "No hay datos para mostrar.")
            return

        vista = tk.Toplevel(self)
        vista.title("Vista Previa")
        vista.geometry("950x600")
        vista.configure(bg="#F9FAFB")

        tree_frame = ttk.Frame(vista, padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columnas = list(self.transformed_df.columns)
        tree = ttk.Treeview(tree_frame, columns=columnas, show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        for col in columnas:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor=tk.CENTER)

        for row in self.transformed_df.itertuples(index=False):
            tree.insert("", "end", values=row)

        ttk.Button(vista, text="Imprimir", command=self._threaded_print).pack(pady=5)

    def _threaded_print(self):
        if self.processing or self.transformed_df is None:
            messagebox.showerror("Error", "Debe cargar un archivo válido primero.")
            return
        threading.Thread(target=self._print_document, daemon=True).start()

    def _print_document(self):
        try:
            printer_map = {
                "fedex": printer_fedex.print_fedex,
                "urbano": printer_urbano.print_urbano,
                "listados": printer_listados.print_listados,
                "etiquetas": printer_etiquetas.print_etiquetas
            }
            imprimir = printer_map.get(self.mode)
            if not imprimir:
                raise ValueError(f"No se encontró función para el modo: {self.mode}")

            imprimir(None, self.config_columns, self.transformed_df)

            save_print_history(
                archivo=f"{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                observacion=f"Impresión realizada en modo '{self.mode}'"
            )

        except Exception as e:
            logging.error(f"Error en impresión: {e}")
            capturar_log_bod1(f"Error al imprimir: {e}", "error")
            self.after(0, lambda: messagebox.showerror("Error", f"Error al imprimir:\n{e}"))

    # ------------------- Configuración y herramientas -------------------

    def _open_config_menu(self):
        if self.df is None:
            messagebox.showerror("Error", "Primero cargue un archivo Excel.")
            return
        self.open_config_dialog(self.mode)

    def open_config_dialog(self, modo: str):
        dialog = ConfigDialog(self, modo, list(self.df.columns), self.config_columns)
        self.wait_window(dialog)
        self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

    def _abrir_editor_etiquetas(self):
        try:
            path = filedialog.askopenfilename(title="Selecciona archivo de etiquetas", filetypes=[("Excel Files", "*.xlsx")])
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

        logs = sorted(log_dir.glob("*.log"), reverse=True)
        if not logs:
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return

        archivo = logs[0]
        win = tk.Toplevel(self)
        win.title(f"Visor de Logs - {archivo.name}")
        win.geometry("1000x600")
        win.configure(bg="#F9FAFB")

        frame = ttk.Frame(win, padding=10)
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
            with archivo.open("r", encoding="utf-8", errors="replace") as f:
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

        ttk.Button(win, text="🔁 Refrescar Log", command=cargar_log).pack(pady=5)
        cargar_log()


def main():
    app = ExcelPrinterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
