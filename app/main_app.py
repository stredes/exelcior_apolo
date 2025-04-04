import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import tempfile
import platform

# ✅ IMPORTS AJUSTADOS A LA NUEVA ESTRUCTURA
from app.config.config_dialog import ConfigDialog
from app.core.excel_processor import validate_file, load_excel, apply_transformation
from app.printer.exporter import export_to_pdf
from app.core.herramientas import abrir_herramientas
from app.db.database import init_db
from app.db.database import save_file_history
from app.core.autoloader import find_latest_file_by_mode, set_carpeta_descarga_personalizada
from app.core.logger_bod1 import capturar_log_bod1
from app.utils.utils import load_config
from app.utils.platform_utils import is_windows, is_linux
from app.gui.etiqueta_editor import crear_editor_etiqueta, cargar_clientes
from app.printer.printer_linux import print_document  # ✅ correctfrom app.printer.printer_linux import print_document  # ✅ con 'app.'



def _get_print_function():
    if platform.system() == "Windows":
        from app.printer.printer import print_document
    elif platform.system() == "Linux":
        from app.printer.printer_linux import print_document
    else:
        raise OSError("Sistema operativo no soportado")
    return print_document


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
        self.print_document = _get_print_function()
        self.mode_vars = {m: tk.BooleanVar(value=(m == "listados")) for m in ["urbano", "fedex", "listados"]}
        self.config_columns = load_config()

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
            ("Ver Logs 📋", self.view_logs),
            ("Herramientas 🛠️", lambda: abrir_herramientas(self, self.transformed_df)),
            ("Etiquetas 🏷️", self._abrir_editor_etiquetas),  # 👈 Aquí está el nuevo botón
        ]

        for text, command in buttons:
            ttk.Button(sidebar, text=text, command=command).pack(pady=10, fill="x", padx=10)

        # Botón "Acerca de"
        ttk.Button(sidebar, text="Acerca de 💼", command=self._mostrar_acerca_de).pack(pady=10, fill="x", padx=10)

        # Botón salir al final
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
        

    def _mostrar_acerca_de(self):
            acerca_win = tk.Toplevel(self)
            acerca_win.title("Acerca de Exelcior Apolo")
            acerca_win.geometry("600x600")
            acerca_win.configure(bg="#F9FAFB")  

            contenido = (
                "🧬 Sistema Exelcior Apolo\n\n"
                "📄 Descripción:\n"
                "Aplicación para facilitar la gestión, edición e impresión de archivos Excel\n"
                "clínicos y logísticos, con herramientas pensadas para el trabajo real en terreno.\n\n"
                "👤 Desarrollador principal:\n"
                "Gian Lucas San Martín\n"
                "• Analista Programador\n"
                "• Técnico de Laboratorio Clínico\n"
                "• Socio fundador de GCNJ\n\n"
                "🤝 Colaboradores:\n"
                "• Mis socios de GCNJ, siempre presentes en el desarrollo de este proyecto\n\n"
                "🔖 Versión: 1.0.0\n"
                "📅 Última actualización: 2025-03-31\n\n"
                "💼 Propiedad:\n"
                "Este software fue creado con fines prácticos y profesionales por el equipo de GCNJ.\n"
                "El código y el diseño pertenecen a sus autores.\n\n"
                "© 2025 Gian Lucas San Martín – GCNJ. Todos los derechos reservados."
            )

            label = tk.Label(acerca_win, text=contenido, justify=tk.LEFT, bg="#F9FAFB", font=("Segoe UI", 10))
            label.pack(padx=20, pady=20)
            

            ttk.Button(acerca_win, text="Cerrar", command=acerca_win.destroy).pack(pady=10)


    def _update_status(self, message):
        self.status_var.set(message)
        self.update_idletasks()

    def _update_mode(self, selected_mode: str):
        for mode in self.mode_vars:
            self.mode_vars[mode].set(mode == selected_mode)
        self.mode = selected_mode

    def _threaded_select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])

        if file_path and validate_file(file_path):
            # Calibrar la carpeta automáticamente
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
                messagebox.showerror("Error", "Ocurrió un error inesperado.")
        except Exception as e:
            self._update_status("❌ Fallo crítico")
            logging.error(f"Error en carga automática: {e}")
            messagebox.showerror("Error", f"No se pudo cargar automáticamente:\n{e}")
        finally:
            self.processing = False


    def _process_file(self, file_path: str):
        self._update_status("Procesando archivo...")
        capturar_log_bod1(f"Iniciando procesamiento del archivo: {file_path}", "info")
        try:
            df = load_excel(file_path, self.config_columns, self.mode)
            self.df = df
            self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)
            save_file_history(file_path, self.mode)
            capturar_log_bod1(f"Archivo procesado correctamente: {file_path}", "info")
            self.after(0, self._show_preview)
        except Exception as exc:
            capturar_log_bod1(f"Error al procesar archivo: {file_path} - {exc}", "error")
            messagebox.showerror("Error", f"Error al leer el archivo:\n{exc}")
            logging.error(f"Error: {exc}")
        finally:
            self.processing = False
            self._update_status("Listo")


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
        ttk.Button(preview_win, text="Cerrar", command=preview_win.destroy).pack(pady=5)


        def eliminar_filas_seleccionadas():
            seleccion = tree.selection()
            if not seleccion:
                messagebox.showinfo("Sin selección", "Debes seleccionar al menos una fila para eliminar.")
                return

            filas_indices = [tree.index(i) for i in seleccion]
            for item in seleccion:
                tree.delete(item)

            # Eliminar del DataFrame original
            self.transformed_df.drop(index=self.transformed_df.index[filas_indices], inplace=True)
            self.transformed_df.reset_index(drop=True, inplace=True)
            capturar_log_bod1(f"Filas eliminadas en vista previa: {filas_indices}", "info")

        ttk.Button(preview_win, text="Eliminar filas seleccionadas", command=eliminar_filas_seleccionadas).pack(pady=5)

        

    def _threaded_print(self):
        if self.processing or self.transformed_df is None:
            messagebox.showerror("Error", "Primero debe cargar un archivo Excel válido.")
            return
        threading.Thread(target=self._print_document, daemon=True).start()

    def _print_document(self):
        try:
            if self.transformed_df is None or self.transformed_df.empty:
                messagebox.showerror("Error", "No hay datos para imprimir.")
                return

            output_dir = Path("exportados/excel")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"{self.mode}_editado_{timestamp}.xlsx"

            # Guardar solamente los datos procesados
            self.transformed_df.to_excel(output_file, index=False)

            capturar_log_bod1(f"Archivo exportado correctamente: {output_file}", "info")

            # Enviar a impresión
            self.print_document(output_file, self.mode, self.config_columns, self.transformed_df)

            messagebox.showinfo("Impresión", f"El documento se ha exportado e impreso correctamente:\n{output_file}")
            capturar_log_bod1(f"Archivo enviado a imprimir: {output_file.name}", "info")

        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir:\n{e}")
            logging.error(f"Error en impresión: {e}")
            capturar_log_bod1(f"Error durante impresión: {e}", "error")



    def _open_config_menu(self):
        if self.df is None:
            messagebox.showerror("Error", "Primero cargue un archivo Excel.")
            return
        self.open_config_dialog(self.mode)
        print("CONFIGURACIÓN CARGADA:", self.config_columns)

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


    def open_config_dialog(self, mode: str):
        dialog = ConfigDialog(self, mode, list(self.df.columns), self.config_columns)
        self.wait_window(dialog)
        self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

    def view_logs(self):
        log_dir = Path("logs")
        if not log_dir.exists():
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return

        log_files = sorted(log_dir.glob("bod1_log_*.log"), reverse=True)
        if not log_files:
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return

        latest_log = log_files[0]
        log_win = tk.Toplevel(self)
        log_win.title(f"Logs: {latest_log.name}")
        log_win.geometry("600x400")
        txt = tk.Text(log_win)
        txt.pack(fill=tk.BOTH, expand=True)
        with latest_log.open("r", encoding="utf-8", errors="replace") as f:
            txt.insert(tk.END, f.read())


if __name__ == "__main__":
    app = ExcelPrinterApp()
    app.mainloop()
