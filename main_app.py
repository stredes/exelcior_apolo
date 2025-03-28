import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import tempfile
import platform

from config_dialog import ConfigDialog
from excel_processor import validate_file, load_excel, apply_transformation
from printer.exporter import export_to_pdf
from herramientas import abrir_herramientas
from utils import load_config, LOG_FILE
from db import init_db, save_file_history

# Detectar sistema operativo
def _get_print_function():
    if platform.system() == "Windows":
        from printer import print_document
    else:
        from printer.printer_linux import print_document_linux as print_document

    return print_document

class ExcelPrinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transformador Excel - Dashboard")
        self.geometry("1000x600")
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
            ("Configuración ⚙️", self._open_config_menu),
            ("Exportar PDF 📄", lambda: export_to_pdf(self.transformed_df, self)),
            ("Ver Logs 📋", self.view_logs),
            ("Herramientas 🛠️", lambda: abrir_herramientas(self, self.transformed_df)),
            ("Salir ❌", self.quit)
        ]

        for text, command in buttons[:-1]:
            ttk.Button(sidebar, text=text, command=command).pack(pady=10, fill="x", padx=10)

        ttk.Button(sidebar, text=buttons[-1][0], command=buttons[-1][1]).pack(side="bottom", pady=20, fill="x", padx=10)

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

    def _update_status(self, message):
        self.status_var.set(message)
        self.update_idletasks()

    def _update_mode(self, selected_mode: str):
        for mode in self.mode_vars:
            self.mode_vars[mode].set(mode == selected_mode)
        self.mode = selected_mode

    def _threaded_select_file(self):
        if self.processing:
            return
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file_path and validate_file(file_path):
            self.processing = True
            threading.Thread(target=self._process_file, args=(file_path,), daemon=True).start()

    def _process_file(self, file_path: str):
        self._update_status("Procesando archivo...")
        try:
            df = load_excel(file_path, self.config_columns, self.mode)
            self.df = df
            self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)
            save_file_history(file_path, self.mode)
            self.after(0, self._show_preview)
        except Exception as exc:
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

            # Crear carpeta de exportación
            output_dir = Path("exportados/excel")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Nombre del archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"{self.mode}_editado_{timestamp}.xlsx"

            # Añadir fila con pie de página (fecha/hora)
            footer_text = f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            footer_df = pd.DataFrame({self.transformed_df.columns[0]: [footer_text]})
            df_con_footer = pd.concat([self.transformed_df, footer_df], ignore_index=True)

            # Guardar archivo con pie de página
            df_con_footer.to_excel(output_file, index=False)

            # Enviar a imprimir
            self.print_document(output_file, self.mode, self.config_columns, self.transformed_df)

            messagebox.showinfo("Impresión", f"El documento se ha exportado e impreso correctamente:\n{output_file}")

        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir:\n{e}")
            logging.error(f"Error en impresión: {e}")

    def _open_config_menu(self):
        if self.df is None:
            messagebox.showerror("Error", "Primero cargue un archivo Excel.")
            return
        self.open_config_dialog(self.mode)
        print("CONFIGURACIÓN CARGADA:", self.config_columns)


    def open_config_dialog(self, mode: str):
        dialog = ConfigDialog(self, mode, list(self.df.columns), self.config_columns)
        self.wait_window(dialog)
        self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

    def view_logs(self):
        if not LOG_FILE.exists():
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return
        log_win = tk.Toplevel(self)
        log_win.title("Logs de la Aplicación")
        log_win.geometry("600x400")
        txt = tk.Text(log_win)
        txt.pack(fill=tk.BOTH, expand=True)
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            txt.insert(tk.END, f.read())

if __name__ == "__main__":
    app = ExcelPrinterApp()
    app.mainloop()
