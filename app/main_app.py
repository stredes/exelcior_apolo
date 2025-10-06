# app/main_app.py
import os
import sys
import logging
import threading
from pathlib import Path
import pandas as pd  # <-- necesario para to_numeric() en _ui_set_status_preview_totals


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

# --- helper para acceder a recursos en dev/pyinstaller ---
def _resource_path(rel_path: str) -> Path:
    """
    Devuelve una ruta válida tanto en desarrollo como en ejecutable PyInstaller.
    Usa sys._MEIPASS cuando está empacado.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return (base / rel_path).resolve()


def _has_display() -> bool:
    """En Linux/Unix, verifica si hay un servidor gráfico disponible."""
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True  # Windows normalmente tiene subsistema gráfico


class ExcelPrinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transformador Excel - Dashboard")
        self.configure(bg="#F9FAFB")
        self._apply_initial_geometry()

        init_db()
        from app.core.logger_eventos import log_evento
        log_evento("Aplicación iniciada", nivel="info", accion="startup")

        # Estado de la app
        self.df = None                 # DF original cargado del Excel
        self.transformed_df = None     # DF que se muestra/imprime (vista previa)
        self.mode = "listados"
        self.processing = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._sidebar_buttons = []
        self._preview_win = None  # la maneja open_preview_crud
        self.sidebar = None

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
        self.bind("<Configure>", self._on_root_resize)

        # Cierre limpio
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- Utilidades GUI seguras ----------------

    def _ui_alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def _apply_initial_geometry(self) -> None:
        """
        Calcula un tamaño de ventana proporcional a la resolución disponible
        y centra la aplicación en pantalla, manteniendo un mínimo cómodo.
        """
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
        except Exception:
            screen_w, screen_h = 1366, 768

        min_w, min_h = 960, 640
        width = max(min_w, int(screen_w * 0.85))
        height = max(min_h, int(screen_h * 0.85))

        width = min(width, screen_w)
        height = min(height, screen_h)

        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)

        self._initial_window_size = (width, height)
        self.minsize(min(width, screen_w), min(height, screen_h))
        self.geometry(f"{width}x{height}+{x}+{y}")


    def _on_root_resize(self, event) -> None:
        """
        Ajusta elementos dependientes del tamaño cuando el usuario
        redimensiona la ventana principal.
        """
        if event.widget is not self:
            return
        if self.sidebar is not None:
            try:
                target_width = max(220, int(event.width * 0.18))
                self.sidebar.configure(width=target_width)
            except Exception:
                pass

    def _sanitize_preview_dataframe(self, df: pd.DataFrame | None, mode: str | None) -> pd.DataFrame | None:
        """
        Limpia filas de resumen (TOTAL) que no se desean en la vista previa,
        actualmente aplicado para el modo Urbano.
        """
        if df is None or df.empty:
            return df

        mode_norm = (mode or "").strip().lower()
        if mode_norm != "urbano":
            return df

        try:
            mask_total = pd.Series(False, index=df.index)
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    continue
                col_values = df[col].astype(str).str.strip().str.upper()
                mask_total = mask_total | (col_values == "TOTAL")
            if mask_total.any():
                df = df.loc[~mask_total].reset_index(drop=True)
        except Exception:
            pass
        return df

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
        initial_width = getattr(self, "_initial_window_size", (1200, 800))[0]
        sidebar_width = max(220, int(initial_width * 0.18))
        sidebar = tk.Frame(self, bg="#111827", width=sidebar_width)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

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

        ttk.Button(sidebar, text="Acerca de 💼", command=self._mostrar_acerca_de).pack(pady=10, fill="x", padx=10)
        ttk.Button(sidebar, text="Salir ❌", command=self._on_close).pack(side="bottom", pady=20, fill="x", padx=10)

    def _setup_main_area(self):
        self.main_frame = tk.Frame(self, bg="#F9FAFB")
        self.main_frame.pack(side="left", fill="both", expand=True)
        self.main_frame.pack_propagate(False)

        tk.Label(self.main_frame, text="Transformador Excel", bg="#F9FAFB", fg="#111827",
                 font=("Segoe UI", 18, "bold")).pack(pady=20, padx=20, fill="x")

        mode_frame = ttk.LabelFrame(self.main_frame, text="Modo de Operación", padding=15)
        mode_frame.pack(fill="x", padx=20, pady=10)

        # Radiobuttons: exclusivo y claro
        for modo in ("listados", "fedex", "urbano"):
            ttk.Radiobutton(
                mode_frame,
                text=modo.capitalize(),
                value=modo,
                variable=self.mode_var,
                command=lambda m=modo: self._update_mode(m)
            ).pack(side=tk.LEFT, expand=True, fill="x", padx=10)

        # -------- LOGO debajo del selector de modo --------
        try:
            from PIL import Image, ImageTk  # pip install pillow

            candidates = [
                "app/data/logo.png",
                "app/data/image.png",
                "app/data/logo.jpg",
                "app/data/image.jpg",
                "app/data/image.ico",
                "data/logo.png",
                "data/image.png",
                "data/image.ico",
            ]
            logo_file = None
            for c in candidates:
                p = _resource_path(c)
                if p.exists():
                    logo_file = p
                    break

            if logo_file is not None:
                img = Image.open(logo_file)
                img.thumbnail((180, 180), Image.LANCZOS)
                self._logo_image = ImageTk.PhotoImage(img)  # guardar referencia
                tk.Label(self.main_frame, image=self._logo_image, bg="#F9FAFB").pack(pady=18)
            else:
                tk.Label(self.main_frame, text="[Logo no encontrado]", bg="#F9FAFB", fg="#c00").pack(pady=18)
        except Exception as e:
            tk.Label(self.main_frame, text=f"[Error cargando logo: {e}]", bg="#F9FAFB", fg="#c00").pack(pady=18)

        self._content_spacer = tk.Frame(self.main_frame, bg="#F9FAFB")
        self._content_spacer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def _setup_status_bar(self):
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=5).pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, mensaje: str):
        if self._ui_alive():
            self.status_var.set(mensaje)

    # NUEVO: pinta totales en barra según DF mostrado
    def _ui_set_status_preview_totals(self, df: pd.DataFrame, mode: str):
        try:
            filas = int(len(df) if df is not None else 0)
            mode_norm = (mode or "").strip().lower()
            if mode_norm == "fedex" and df is not None and "BULTOS" in df.columns:
                total_bultos = int(pd.to_numeric(df["BULTOS"], errors="coerce").fillna(0).sum())
                self._update_status(f"Filas: {filas} | Total BULTOS: {total_bultos}")
            elif mode_norm == "urbano" and df is not None and "PIEZAS" in df.columns:
                total_piezas = int(pd.to_numeric(df["PIEZAS"], errors="coerce").fillna(0).sum())
                self._update_status(f"Filas: {filas} | Total PIEZAS: {total_piezas}")
            else:
                self._update_status(f"Filas: {filas}")
        except Exception:
            self._update_status("")

    # ---------------- Acciones de modo ----------------

    def _update_mode(self, modo_seleccionado: str):
        self.mode = modo_seleccionado
        from app.core.logger_eventos import log_evento
        log_evento(f"Modo cambiado a: {modo_seleccionado}", nivel="info", accion="cambio_modo")

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
        from app.core.logger_eventos import log_evento
        if self.processing:
            return
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls *.csv")])
        if not path:
            return
        valid, err = validate_file(path)
        if not valid:
            self.safe_messagebox("error", "Archivo no válido", err)
            log_evento(f"Archivo no válido seleccionado: {path}", nivel="warning", accion="seleccion_archivo")
            return
        set_carpeta_descarga_personalizada(Path(path).parent, self.mode)
        log_evento(f"Archivo seleccionado: {path}", nivel="info", accion="seleccion_archivo")
        self.processing = True
        self._set_controls_enabled(False)
        future = self.executor.submit(process_file, path, self.config_columns, self.mode)
        future.add_done_callback(self._file_processed_callback)

    def _file_processed_callback(self, future):
        from app.core.logger_eventos import log_evento
        try:
            df, transformed = future.result()
            if not self._ui_alive():
                return
            self.df = df
            mode_norm = (self.mode or "").strip().lower()
            if mode_norm == "fedex" and self.df is not None:
                self.transformed_df, _, _ = prepare_fedex_dataframe(self.df)
            else:
                self.transformed_df = transformed
            self.transformed_df = self._sanitize_preview_dataframe(self.transformed_df, mode_norm)
            save_file_history("n/a", self.mode)
            self._ui_set_status_preview_totals(self.transformed_df, self.mode)
            log_evento("Archivo procesado correctamente", nivel="info", accion="procesamiento_archivo")
            self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
        except Exception as e:
            logging.exception("Error al procesar archivo")
            log_evento(f"Error al procesar archivo: {e}", nivel="error", accion="procesamiento_archivo", exc=e)
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
            transformed_base = apply_transformation(self.df, self.config_columns, self.mode)

            # Vista Previa FedEx: construir desde DF original
            mode_norm = (self.mode or "").strip().lower()
            if mode_norm == "fedex":
                self.transformed_df, _, _ = prepare_fedex_dataframe(self.df)
            else:
                self.transformed_df = transformed_base

            self.transformed_df = self._sanitize_preview_dataframe(self.transformed_df, mode_norm)

            save_file_history(path, self.mode)
            self._ui_set_status_preview_totals(self.transformed_df, self.mode)
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
            # Reaplica transformación base por si hay reglas para otros modos
            transformed_base = apply_transformation(self.df, self.config_columns, self.mode)

            # Vista Previa FedEx: construir desde DF original
            mode_norm = (self.mode or "").strip().lower()
            if mode_norm == "fedex":
                self.transformed_df, _, _ = prepare_fedex_dataframe(self.df)
            else:
                self.transformed_df = transformed_base

            self.transformed_df = self._sanitize_preview_dataframe(self.transformed_df, mode_norm)

            self._ui_set_status_preview_totals(self.transformed_df, self.mode)
            if self._ui_alive():
                self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
        except Exception as e:
            logging.error(f"Error reaplicando reglas: {e}")

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


