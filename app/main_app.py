# app/main_app.py
import os
import sys
import logging
import threading
import subprocess
from pathlib import Path


# Asegura que la raíz del proyecto esté en sys.path para evitar errores de importación
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor

# ✅ Lógica de negocio / servicios
from app.services.file_service import (
    validate_file,
    process_file,
    print_document,
    build_preview_dataframe,
    compute_preview_stats,
)
from app.db.database import init_db, save_file_history, save_print_history
from app.config.config_dialog import ConfigDialog  # Configuración por MODO
from app.core.autoloader import find_latest_file_by_mode, set_carpeta_descarga_personalizada
from app.core.logger_eventos import capturar_log_bod1
from app.config.config_manager import load_config
from app.gui.etiqueta_editor import crear_editor_etiqueta
from app.gui.sra_mary import SraMaryView
from app.gui.inventario_view import InventarioView

# 🔽 Vista previa + CRUD externalizada (ventana + widget)
from app.gui.preview_crud import open_preview_crud

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
    REPORT_DEFAULT_PRINTER = "Brother DCP-L5650DN series [b422002bd4a6]"
    LABEL_DEFAULT_PRINTER = "URBANO"

    def __init__(self):
        super().__init__()
        self.title("Transformador Excel - Dashboard")
        self.configure(bg="#F3F6FB")
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
        self._mode_buttons = {}

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
        self._apply_default_printer_for_report_mode()

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
        try:
            style.theme_use("clam")
        except Exception:
            try:
                style.theme_use(style.theme_names()[0])
            except Exception:
                pass

        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=7)
        style.configure("TLabel", font=("Segoe UI", 10), background="#F3F6FB")
        style.configure("TCheckbutton", font=("Segoe UI", 10))
        style.configure("TRadiobutton", font=("Segoe UI", 10))
        style.configure(
            "Sidebar.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(12, 9),
            borderwidth=0,
            relief="flat",
            foreground="#E5ECFF",
            background="#1A2742",
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", "#24365B"), ("disabled", "#111C34")],
            foreground=[("active", "#FFFFFF"), ("disabled", "#6C7A9B")],
        )
        style.configure(
            "SidebarExit.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(12, 9),
            borderwidth=0,
            relief="flat",
            foreground="#FFE4E6",
            background="#8A2130",
        )
        style.map(
            "SidebarExit.TButton",
            background=[("active", "#A02A3B"), ("disabled", "#5F1723")],
            foreground=[("active", "#FFFFFF"), ("disabled", "#D0AAB1")],
        )
        style.configure("Mode.TLabelframe", padding=14, background="#FFFFFF")
        style.configure("Mode.TLabelframe.Label", font=("Segoe UI Semibold", 11), background="#FFFFFF")
        style.configure("Status.TLabel", font=("Segoe UI", 10), padding=8, background="#0F172A", foreground="#E2E8F0")
        style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 26), foreground="#0B1730", background="#FFFFFF")
        style.configure("CardSub.TLabel", font=("Segoe UI", 10), foreground="#4B5C7A", background="#FFFFFF")

    def _add_sidebar_button(self, parent, text, cmd):
        b = ttk.Button(parent, text=text, command=cmd, style="Sidebar.TButton")
        b.pack(pady=6, fill="x", padx=12)
        self._sidebar_buttons.append(b)
        return b

    def _setup_sidebar(self):
        initial_width = getattr(self, "_initial_window_size", (1200, 800))[0]
        sidebar_width = max(220, int(initial_width * 0.18))
        sidebar = tk.Frame(self, bg="#0B1730", width=sidebar_width)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        tk.Label(sidebar, text="Menu", bg="#0B1730", fg="#F8FAFC",
                 font=("Segoe UI Semibold", 16)).pack(pady=(20, 6))
        tk.Label(sidebar, text="Operaciones", bg="#0B1730", fg="#91A4CC",
                 font=("Segoe UI", 9)).pack(pady=(0, 14))

        self._add_sidebar_button(sidebar, "Seleccionar Excel", self._threaded_select_file)
        self._add_sidebar_button(sidebar, "Carga Automatica", self._threaded_auto_load)
        self._add_sidebar_button(sidebar, "Configurar Modo", self._open_config_menu)
        self._add_sidebar_button(sidebar, "Ver Logs", self._view_logs)
        self._add_sidebar_button(sidebar, "Etiquetas", self._abrir_editor_etiquetas)
        self._add_sidebar_button(sidebar, "Codigos Postales", self._abrir_buscador_codigos_postales)
        self._add_sidebar_button(sidebar, "Sra Mary", self._abrir_sra_mary)
        self._add_sidebar_button(sidebar, "Inventario", lambda: InventarioView(self))
        self._add_sidebar_button(sidebar, "Vale de Consumo", self._abrir_vale_consumo)

        footer = tk.Frame(sidebar, bg="#0B1730")
        footer.pack(side="bottom", fill="x", padx=12, pady=(10, 14))
        ttk.Separator(footer, orient="horizontal").pack(fill="x", pady=(0, 10))
        tk.Button(
            footer,
            text="Salir",
            command=self._on_close,
            font=("Segoe UI Semibold", 10),
            bg="#8A2130",
            fg="#FFE4E6",
            activebackground="#A02A3B",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=8,
        ).pack(fill="x")

    def _setup_main_area(self):
        self.main_frame = tk.Frame(self, bg="#F3F6FB")
        self.main_frame.pack(side="left", fill="both", expand=True)
        self.main_frame.pack_propagate(False)

        hero = tk.Frame(self.main_frame, bg="#FFFFFF", bd=1, relief="solid", highlightthickness=0)
        hero.pack(fill="x", padx=24, pady=(24, 10))

        ttk.Label(hero, text="Transformador Excel", style="CardTitle.TLabel", anchor="center").pack(
            pady=(18, 6), padx=20, fill="x"
        )
        ttk.Label(
            hero,
            text="Carga, transforma y envia reportes desde una sola interfaz.",
            style="CardSub.TLabel",
            anchor="center",
        ).pack(pady=(0, 14), padx=20, fill="x")
        mode_frame = ttk.LabelFrame(
            hero,
            text="Modo de Operacion",
            padding=12,
            style="Mode.TLabelframe",
        )
        mode_frame.pack(fill="x", padx=20, pady=(0, 18))

        mode_strip = tk.Frame(mode_frame, bg="#FFFFFF")
        mode_strip.pack(fill="x")

        labels = {"listados": "Listados", "fedex": "Fedex", "urbano": "Urbano"}
        for modo in ("listados", "fedex", "urbano"):
            rb = tk.Radiobutton(
                mode_strip,
                text=labels[modo],
                value=modo,
                variable=self.mode_var,
                indicatoron=False,
                relief="flat",
                bd=0,
                command=lambda m=modo: self._update_mode(m),
                font=("Segoe UI Semibold", 10),
                padx=14,
                pady=8,
                cursor="hand2",
                selectcolor="#1E3A8A",
            )
            rb.pack(side=tk.LEFT, expand=True, fill="x", padx=6, pady=2)
            self._mode_buttons[modo] = rb
        self._refresh_mode_buttons()

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
                logo_card = tk.Frame(self.main_frame, bg="#FFFFFF", bd=1, relief="solid", highlightthickness=0)
                logo_card.pack(pady=18, padx=24)
                tk.Label(logo_card, image=self._logo_image, bg="#FFFFFF").pack(padx=20, pady=18)
            else:
                tk.Label(self.main_frame, text="[Logo no encontrado]", bg="#F3F6FB", fg="#c00").pack(pady=18)
        except Exception as e:
            tk.Label(self.main_frame, text=f"[Error cargando logo: {e}]", bg="#F3F6FB", fg="#c00").pack(pady=18)

        self._content_spacer = tk.Frame(self.main_frame, bg="#F3F6FB")
        self._content_spacer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def _setup_status_bar(self):
        self.status_var = tk.StringVar()
        status_frame = tk.Frame(self, bg="#0F172A")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W, style="Status.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    def _refresh_mode_buttons(self):
        active_mode = self.mode_var.get().strip().lower()
        for mode, btn in self._mode_buttons.items():
            is_active = mode == active_mode
            btn.configure(
                bg="#1E3A8A" if is_active else "#E8EDF8",
                fg="#FFFFFF" if is_active else "#1A2B4F",
                activebackground="#2747A6" if is_active else "#D9E3F6",
                activeforeground="#FFFFFF" if is_active else "#1A2B4F",
            )

    def _update_status(self, mensaje: str):
        if self._ui_alive():
            self.status_var.set(mensaje)

    def _ui_set_status_preview_totals(self, df, mode: str):
        try:
            stats = compute_preview_stats(df, mode)
            filas = int(stats.get("rows", 0))
            metric_label = stats.get("metric_label")
            metric_value = stats.get("metric_value")
            if metric_label is not None and metric_value is not None:
                self._update_status(f"Filas: {filas} | Total {metric_label}: {metric_value}")
            else:
                self._update_status(f"Filas: {filas}")
        except Exception:
            self._update_status("")

    def _publish_preview(self, df, transformed, history_path: str):
        """Aplica resultado de procesamiento y refresca vista previa/UI de forma uniforme."""
        self.df = df
        self.transformed_df = transformed
        save_file_history(history_path, self.mode)
        self._ui_set_status_preview_totals(self.transformed_df, self.mode)
        if self._ui_alive():
            self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))

    def _close_preview_window(self):
        try:
            if self._preview_win is not None and self._preview_win.winfo_exists():
                self._preview_win.destroy()
        except Exception:
            pass
        finally:
            self._preview_win = None

    # ---------------- Acciones de modo ----------------

    def _update_mode(self, modo_seleccionado: str):
        self.mode = modo_seleccionado
        self.mode_var.set(modo_seleccionado)
        self._refresh_mode_buttons()
        self._apply_default_printer_for_report_mode()
        from app.core.logger_eventos import log_evento
        log_evento(f"Modo cambiado a: {modo_seleccionado}", nivel="info", accion="cambio_modo")

    def _resolve_windows_printer_name(self, alias: str) -> str:
        base = (alias or "").strip()
        if not base or not sys.platform.startswith("win"):
            return base
        try:
            import win32print  # type: ignore

            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            names = []
            for item in win32print.EnumPrinters(flags):
                try:
                    n = str(item[2]).strip()
                except Exception:
                    continue
                if n:
                    names.append(n)
            low = base.lower()
            for n in names:
                if n.lower() == low:
                    return n
            for n in names:
                if low in n.lower() or n.lower() in low:
                    return n
        except Exception:
            pass
        return base

    def _set_windows_default_printer(self, printer_alias: str) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            import win32print  # type: ignore

            resolved = self._resolve_windows_printer_name(printer_alias)
            if not resolved:
                return
            win32print.SetDefaultPrinter(resolved)
            logging.info(f"[PrinterSwitch] Default aplicada: {resolved}")
        except Exception as e:
            logging.warning(f"[PrinterSwitch] No se pudo cambiar default a '{printer_alias}': {e}")

    def _apply_default_printer_for_report_mode(self) -> None:
        # Los 3 modos de informe salen siempre por la Brother.
        self._set_windows_default_printer(self.REPORT_DEFAULT_PRINTER)

    def _apply_default_printer_for_labels(self) -> None:
        # Etiquetas: prioriza lo guardado en config; fallback 'URBANO'.
        label_printer = (
            self.config_columns.get("printer_name")
            if isinstance(self.config_columns, dict)
            else None
        ) or self.LABEL_DEFAULT_PRINTER
        self._set_windows_default_printer(str(label_printer))

    def _abrir_buscador_codigos_postales(self):
        from app.gui.buscador_codigos_postales import BuscadorCodigosPostales
        BuscadorCodigosPostales(self)

    def _abrir_sra_mary(self):
        SraMaryView(self)

    def _abrir_vale_consumo(self):
        """
        Abre la app de Vale de Consumo (Bioplates) en una ventana separada.

        - En desarrollo: lanza vale_consumo/run_app.py con el intérprete actual.
        - En ejecutable PyInstaller: intenta abrir ValeConsumoBioplates.exe
          ubicado junto a ExelciorApolo.exe o en una subcarpeta 'vale_consumo'.
        """
        try:
            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).resolve().parent
                candidates = [
                    base_dir / "ValeConsumoBioplates.exe",
                    base_dir / "vale_consumo" / "ValeConsumoBioplates.exe",
                ]
                for exe_path in candidates:
                    if exe_path.exists():
                        subprocess.Popen([str(exe_path)])
                        return
                self.safe_messagebox(
                    "error",
                    "Vale de Consumo",
                    "No se encontró 'ValeConsumoBioplates.exe'.\n"
                    "Copia el ejecutable de vales junto a ExelciorApolo.exe "
                    "o dentro de una carpeta 'vale_consumo' y vuelve a intentarlo.",
                )
                return

            script_path = (ROOT_DIR / "vale_consumo" / "run_app.py").resolve()
            if not script_path.exists():
                self.safe_messagebox(
                    "error",
                    "Vale de Consumo",
                    "No se encontró 'vale_consumo/run_app.py' en la carpeta del proyecto.",
                )
                return
            python = sys.executable or "python"
            subprocess.Popen([python, str(script_path)])
        except Exception as e:
            logging.exception("Error lanzando Vale de Consumo")
            self.safe_messagebox("error", "Vale de Consumo", f"No se pudo abrir la app de vales:\n{e}")

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
            self._publish_preview(df, transformed, history_path="n/a")
            log_evento("Archivo procesado correctamente", nivel="info", accion="procesamiento_archivo")
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
            df, transformed = process_file(path, self.config_columns, self.mode)
            self._publish_preview(df, transformed, history_path=path)
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
                self._close_preview_window()
                self.safe_messagebox("info", "Listo", "Impresion completada.")
                self._update_status("Impresion completada. Vista previa cerrada.")
        except Exception as e:
            logging.exception("Error impresion")
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
            self.transformed_df = build_preview_dataframe(self.df, self.config_columns, self.mode)
            self._ui_set_status_preview_totals(self.transformed_df, self.mode)
            if self._ui_alive():
                self.after(0, lambda: open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print))
        except Exception as e:
            logging.error(f"Error reaplicando reglas: {e}")

    # ---------------- Otras vistas ----------------

    def _abrir_editor_etiquetas(self):
        try:
            self._apply_default_printer_for_labels()
            win = crear_editor_etiqueta(parent=self)
            if win is not None:
                win.bind("<Destroy>", lambda _e: self._apply_default_printer_for_report_mode())
        except Exception as e:
            self.safe_messagebox("error", "Error", f"No se pudo abrir el editor de etiquetas:\n{e}")

    def _view_logs(self):
        root_logs = Path(__file__).resolve().parent.parent / "logs"
        legacy_logs = Path(__file__).resolve().parent / "logs"  # app/logs (ruta antigua)
        cwd_logs = Path.cwd() / "logs"
        cwd_legacy_logs = Path.cwd() / "app" / "logs"
        search_dirs = (root_logs, legacy_logs, cwd_logs, cwd_legacy_logs)
        for d in search_dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        candidatos = set()
        for d in search_dirs:
            candidatos.update(d.glob("*.log"))
            candidatos.update(d.glob("*.log.*"))  # incluye logs rotados (TimedRotatingFileHandler)

        logs = sorted(
            {p.resolve() for p in candidatos if p.is_file()},
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not logs:
            self.safe_messagebox(
                "info",
                "Logs",
                "No hay logs para mostrar.\nBuscado en:\n- "
                + "\n- ".join(str(p) for p in search_dirs),
            )
            return

        # Prioriza el log más reciente con contenido para evitar abrir archivos vacíos.
        archivo = next((p for p in logs if p.stat().st_size > 0), logs[0])
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
        self._close_preview_window()
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


