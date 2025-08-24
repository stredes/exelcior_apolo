# app/main_app.py
import os
import sys
import logging
import threading
from pathlib import Path

# Asegura que la raíz del proyecto esté en sys.path para evitar errores de importación
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor

# ✅ Lógica de negocio / servicios
from app.services.file_service import validate_file, process_file, print_document
from app.db.database import init_db, save_file_history, save_print_history
from app.config.config_dialog import ConfigDialog  # Configuración por MODO
from app.core.autoloader import find_latest_file_by_mode, set_carpeta_descarga_personalizada
from app.core.logger_eventos import capturar_log_bod1
from app.config.config_manager import load_config
from app.gui.etiqueta_editor import crear_editor_etiqueta, cargar_clientes
from app.gui.sra_mary import SraMaryView
from app.gui.inventario_view import InventarioView
from app.printer.exporter import export_to_pdf
from app.gui.herramientas_gui import abrir_herramientas
from app.core.excel_processor import load_excel, apply_transformation

# 🔽 Vista previa + CRUD externalizada (ventana + widget)
from app.gui.preview_crud import open_preview_crud

# 🔽 Post-proceso FedEx (shaping/dedupe/total BULTOS)
from app.printer.printer_tools import prepare_fedex_dataframe


# (Opcional) GUI de ajustes del sistema
try:
    from app.gui.gui_config import open_system_config  # si existe
except Exception:
    open_system_config = None


def _has_display() -> bool:
    """En Linux/Unix, verifica si hay un servidor gráfico disponible."""
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True  # Windows normalmente tiene subsistema gráfico


class ExcelPrinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transformador Excel - Dashboard")
        self.geometry("850x720")
        self.configure(bg="#F9FAFB")

        init_db()

        # Estado de la app
        self.df = None
        self.transformed_df = None
        self.mode = "listados"
        self.processing = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._sidebar_buttons = []
        self._preview_win: tk.Toplevel | None = None  # la maneja open_preview_crud

        # ✅ Carga de config robusta
        try:
            config = load_config()
            if not isinstance(config, dict):
                logging.warning("[CONFIG] load_config no devolvió dict; usando {}")
                config = {}
        except Exception:
            logging.exception("[CONFIG] Error cargando configuración; usando {}")
            config = {}

        self.config_columns = config

        # 🎛️ Selector de modo (Radiobutton para exclusividad)
        self.mode_var = tk.StringVar(value="listados")

        self._setup_styles()
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_status_bar()

        # Cierre limpio
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- Utilidades GUI seguras ----------------

    def _ui_alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def safe_messagebox(self, tipo: str, titulo: str, mensaje: str):
        """Muestra messagebox desde hilos de fondo sin romper Tk y tolera entorno sin DISPLAY."""
        if not self._ui_alive() or not _has_display():
            logging.info(f"[MSGBOX suppressed] {tipo.upper()} - {titulo}: {mensaje}")
            return
        try:
            tipo_map = {
                "info": messagebox.showinfo,
                "warning": messagebox.showwarning,
                "error": messagebox.showerror,
            }
            fn = tipo_map.get(tipo, messagebox.showinfo)
            self.after(0, lambda: fn(titulo, mensaje))
        except Exception:
            pass

    def _set_controls_enabled(self, enabled: bool):
        """Habilita/deshabilita botones de la barra lateral durante procesamiento."""
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in self._sidebar_buttons:
            try:
                btn.configure(state=state)
            except Exception:
                pass

    # ---------------- Setup UI ----------------

    def _setup_styles(self):
        style = ttk.Style(self)
        # Fallback de tema para Linux (algunas distros no tienen 'clam' por defecto)
        try:
            style.theme_use('clam')
        except Exception:
            # Elige el primero disponible
            try:
                style.theme_use(style.theme_names()[0])
            except Exception:
                pass

        style.configure("TButton", font=("Segoe UI", 11), padding=8)
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TCheckbutton", font=("Segoe UI", 11))
        style.configure("TRadiobutton", font=("Segoe UI", 11))

    def _add_sidebar_button(self, parent, text, cmd):
        b = ttk.Button(parent, text=text, command=cmd)
        b.pack(pady=10, fill="x", padx=10)
        self._sidebar_buttons.append(b)
        return b

    def _setup_sidebar(self):
        sidebar = tk.Frame(self, bg="#111827", width=220)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="Menú", bg="#111827", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(pady=20)

        self._add_sidebar_button(sidebar, "Seleccionar Excel 📂", self._threaded_select_file)
        self._add_sidebar_button(sidebar, "Carga Automática 🚀", self._threaded_auto_load)
        self._add_sidebar_button(sidebar, "Config. Modo ⚙️", self._open_config_menu)  # diálogo por MODO
        self._add_sidebar_button(sidebar, "Exportar PDF 📄", lambda: export_to_pdf(self.transformed_df, self))
        self._add_sidebar_button(sidebar, "Ver Logs 📋", self._view_logs)
        self._add_sidebar_button(sidebar, "Herramientas 🛠️", lambda: abrir_herramientas(self, self.transformed_df))
        self._add_sidebar_button(sidebar, "Etiquetas 🏷️", self._abrir_editor_etiquetas)
        self._add_sidebar_button(sidebar, "Buscar Códigos Postales 🧽", self._abrir_buscador_codigos_postales)
        self._add_sidebar_button(sidebar, "Sra Mary 👩‍💼", self._abrir_sra_mary)
        self._add_sidebar_button(sidebar, "Inventario 📦", lambda: InventarioView(self))

        # Si la GUI de ajustes del sistema está disponible, añade botón
        if open_system_config:
            self._add_sidebar_button(sidebar, "Ajustes del Sistema 🌐",
                                     lambda: open_system_config(self, self._on_system_config_saved))

        ttk.Button(sidebar, text="Acerca de 💼", command=self._mostrar_acerca_de).pack(pady=10, fill="x", padx=10)
        ttk.Button(sidebar, text="Salir ❌", command=self._on_close).pack(side="bottom", pady=20, fill="x", padx=10)

    def _setup_main_area(self):
        self.main_frame = tk.Frame(self, bg="#F9FAFB")
        self.main_frame.pack(side="left", fill="both", expand=True)

        tk.Label(self.main_frame, text="Transformador Excel", bg="#F9FAFB", fg="#111827",
                 font=("Segoe UI", 18, "bold")).pack(pady=20)

        mode_frame = ttk.LabelFrame(self.main_frame, text="Modo de Operación", padding=15)
        mode_frame.pack(pady=10)

        # Radiobuttons: exclusivo y claro
        for modo in ("listados", "fedex", "urbano"):
            ttk.Radiobutton(
                mode_frame,
                text=modo.capitalize(),
                value=modo,
                variable=self.mode_var,
                command=lambda m=modo: self._update_mode(m)
            ).pack(side=tk.LEFT, padx=10)

    def _setup_status_bar(self):
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=5).pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, mensaje: str):
        if self._ui_alive():
            self.status_var.set(mensaje)

    # ---------------- Acciones de modo ----------------

    def _update_mode(self, modo_seleccionado: str):
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
        self.safe_messagebox("info", "Acerca de", mensaje)

    # ---------------- Carga de archivos ----------------

    def _threaded_select_file(self):
        if self.processing:
            return
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls *.csv")])
        if not path:
            return
        valid, err = validate_file(path)
        if not valid:
            self.safe_messagebox("error", "Archivo no válido", err)
            return
        set_carpeta_descarga_personalizada(Path(path).parent, self.mode)
        self.processing = True
        self._set_controls_enabled(False)
        future = self.executor.submit(process_file, path, self.config_columns, self.mode)
        future.add_done_callback(self._file_processed_callback)

    def _file_processed_callback(self, future):
        try:
            df, transformed = future.result()
            if not self._ui_alive():
                return
            self.df, self.transformed_df = df, transformed

            # 🔽 Post-proceso para Vista Previa en modo FedEx (dedupe + consolidación)
            if (self.mode or "").strip().lower() == "fedex" and self.transformed_df is not None:
                self.transformed_df, _, _ = prepare_fedex_dataframe(self.transformed_df)

            save_file_history("n/a", self.mode)
            self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
        except Exception as e:
            logging.exception("Error al procesar archivo")
            if self._ui_alive():
                self.safe_messagebox("error", "Error", str(e))
                self.after(0, lambda: self._update_status("Error"))
        finally:
            self.processing = False
            self._set_controls_enabled(True)

    def _threaded_auto_load(self):
        if self.processing:
            return
        self.processing = True
        self._set_controls_enabled(False)
        t = threading.Thread(target=self._auto_load_latest_file, daemon=True)
        t.start()

    def _auto_load_latest_file(self):
        self._update_status("Buscando archivo más reciente...")
        try:
            archivo, estado = find_latest_file_by_mode(self.mode)
            if estado == "ok" and archivo:
                valido, msg = validate_file(str(archivo))
                if not valido:
                    self._update_status(f"⚠️ Archivo más reciente inválido: {msg}")
                    self.safe_messagebox("error", "Archivo no válido", msg)
                    return
                self._update_status(f"✅ Cargado: {archivo.name}")
                self._process_file(str(archivo))
            elif estado == "no_match":
                self._update_status("⚠️ No se encontraron archivos compatibles.")
                self.safe_messagebox("warning", "Sin coincidencias", f"No hay archivos válidos para el modo '{self.mode}'")
            elif estado == "empty_folder":
                self._update_status("📂 Carpeta vacía o inexistente.")
                self.safe_messagebox("error", "Carpeta vacía", "La carpeta de descargas está vacía o no existe.")
            else:
                self._update_status("❌ Error en la autocarga.")
        except Exception as e:
            logging.error(f"Error en carga automática: {e}")
            self.safe_messagebox("error", "Error", str(e))
        finally:
            self.processing = False
            self._set_controls_enabled(True)

    def _process_file(self, path: str):
        self._update_status("Procesando archivo...")
        capturar_log_bod1(f"Iniciando procesamiento: {path}", "info")
        try:
            self.df = load_excel(path, self.config_columns, self.mode)
            self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

            # 🔽 Post-proceso para Vista Previa en modo FedEx (dedupe + consolidación)
            if (self.mode or "").strip().lower() == "fedex" and self.transformed_df is not None:
                self.transformed_df, _, _ = prepare_fedex_dataframe(self.transformed_df)

            save_file_history(path, self.mode)
            if self._ui_alive():
                self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
        except Exception as e:
            logging.error(f"Error procesando archivo: {e}")
            self.safe_messagebox("error", "Error", f"No se pudo procesar el archivo:\n{e}")
        finally:
            self._update_status("Listo")

    # ---------------- Impresión ----------------

    def _threaded_print(self):
        if self.processing or self.transformed_df is None or self.transformed_df.empty:
            self.safe_messagebox("error", "Error", "Debe cargar un archivo válido primero.")
            return
        self.processing = True
        self._set_controls_enabled(False)
        future = self.executor.submit(self._print_document)
        future.add_done_callback(self._print_complete_callback)

    def _print_complete_callback(self, future):
        try:
            future.result()
            if self._ui_alive():
                self.safe_messagebox("info", "Listo", "Impresión completada.")
                self._update_status("Listo")
        except Exception as e:
            logging.exception("Error impresión")
            if self._ui_alive():
                self.safe_messagebox("error", "Error", str(e))
                self._update_status("Error")
        finally:
            self.processing = False
            self._set_controls_enabled(True)

    def _print_document(self):
        try:
            # Imprime exactamente lo que está en la vista previa/CRUD
            print_document(self.mode, self.transformed_df, self.config_columns, None)
            save_print_history(
                archivo=f"{self.mode}_impresion.xlsx",
                observacion=f"Impresión realizada en modo '{self.mode}'"
            )
            self.df = None
            self.transformed_df = None
        except Exception as e:
            logging.error(f"Error en impresión: {e}")
            capturar_log_bod1(f"Error al imprimir: {e}", "error")
            if self._ui_alive():
                msg = f"Error al imprimir:\n{e}"
                self.after(0, lambda m=msg: self.safe_messagebox("error", "Error", m))
            raise

    # ---------------- Configuración ----------------

    def _open_config_menu(self):
        if self.df is None:
            self.safe_messagebox("error", "Error", "Primero cargue un archivo Excel.")
            return
        self.open_config_dialog(self.mode)

    def open_config_dialog(self, modo: str):
        # Editor por MODO (listados / fedex / urbano)
        dialog = ConfigDialog(self, modo, list(self.df.columns), self.config_columns)
        self.wait_window(dialog)
        # Reaplicar reglas tras guardar para reflejarse en la vista previa
        try:
            self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

            # 🔽 Post-proceso para Vista Previa en modo FedEx (dedupe + consolidación)
            if (self.mode or "").strip().lower() == "fedex" and self.transformed_df is not None:
                self.transformed_df, _, _ = prepare_fedex_dataframe(self.transformed_df)

            if self._ui_alive():
                self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
        except Exception as e:
            logging.error(f"Error reaplicando reglas: {e}")

    # 👉 Callback cuando se guardan los “Ajustes del Sistema”
    def _on_system_config_saved(self, new_cfg: dict):
        self.config_columns = new_cfg or {}
        if self.df is not None:
            try:
                self.transformed_df = apply_transformation(self.df, self.config_columns, self.mode)

                # 🔽 Post-proceso para Vista Previa en modo FedEx (dedupe + consolidación)
                if (self.mode or "").strip().lower() == "fedex" and self.transformed_df is not None:
                    self.transformed_df, _, _ = prepare_fedex_dataframe(self.transformed_df)

                if self._ui_alive():
                    self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
            except Exception as e:
                logging.error(f"Error aplicando reglas tras guardar ajustes del sistema: {e}")

    # ---------------- Otras vistas ----------------

    def _abrir_editor_etiquetas(self):
        try:
            path = filedialog.askopenfilename(title="Selecciona archivo de etiquetas",
                                              filetypes=[("Excel Files", "*.xlsx")])
            if not path:
                return
            df_clientes = cargar_clientes(path)
            crear_editor_etiqueta(df_clientes)
        except Exception as e:
            self.safe_messagebox("error", "Error", f"No se pudo abrir el editor de etiquetas:\n{e}")

    def _view_logs(self):
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        # 🔧 Asegura que exista en Linux
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        if not log_dir.exists():
            self.safe_messagebox("info", "Logs", "No hay logs para mostrar.")
            return

        logs = sorted(log_dir.glob("*.log"), reverse=True)
        if not logs:
            self.safe_messagebox("info", "Logs", "No hay logs para mostrar.")
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
            try:
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
            except Exception as e:
                logging.error(f"Error leyendo log: {e}")

        ttk.Button(win, text="🔁 Refrescar Log", command=cargar_log).pack(pady=5)
        cargar_log()

    # ---------------- Cierre limpio ----------------

    def _on_close(self):
        try:
            self.processing = False
            if self.executor:
                self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        try:
            if self._preview_win is not None and self._preview_win.winfo_exists():
                self._preview_win.destroy()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


def setup_logging():
    log_dir = (Path(__file__).resolve().parent.parent / "logs")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(log_dir / "app.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_app():
    app = ExcelPrinterApp()
    app.mainloop()


def main():
    setup_logging()
    # Si no hay servidor gráfico, informa y aborta con código claro
    if not _has_display():
        logging.error("No se detectó DISPLAY/servidor gráfico. La interfaz Tkinter requiere entorno gráfico.")
        print("Error: No se detectó entorno gráfico (DISPLAY/Wayland).")
        sys.exit(2)

    try:
        run_app()
    except Exception as e:
        logging.exception("Error fatal en la aplicación")
        try:
            # Solo intentes messagebox si hay display
            if _has_display():
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error crítico", f"Ocurrió un error fatal:\n{e}")
                root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
