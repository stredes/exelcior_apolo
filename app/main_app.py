# app/main_app.py
import os
import sys
import logging
import threading
import subprocess
from pathlib import Path


# Asegura que la raÃ­z del proyecto estÃ© en sys.path para evitar errores de importaciÃ³n
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor

# âœ… LÃ³gica de negocio / servicios
from app.services.file_service import (
    validate_file,
    process_file,
    print_document,
    build_preview_dataframe,
    compute_preview_stats,
)
from app.db.database import init_db, save_file_history, save_print_history
from app.config.config_dialog import ConfigDialog  # ConfiguraciÃ³n por MODO
from app.core.autoloader import find_latest_file_by_mode, set_carpeta_descarga_personalizada
from app.core.logger_eventos import capturar_log_bod1
from app.config.config_manager import load_config
from app.gui.etiqueta_editor import crear_editor_etiqueta, cargar_config as cargar_config_etiquetas
from app.gui.sra_mary import SraMaryView
from app.gui.inventario_view import InventarioView
from app.gui.printer_admin import PrinterAdminDialog
from app.updater import (
    fetch_latest_release,
    get_local_version,
    is_newer_version,
    launch_installer,
    parse_release_info,
    start_update_download,
)

# ðŸ”½ Vista previa + CRUD externalizada (ventana + widget)
from app.gui.preview_crud import open_preview_crud

# --- helper para acceder a recursos en dev/pyinstaller ---
def _resource_path(rel_path: str) -> Path:
    """
    Devuelve una ruta vÃ¡lida tanto en desarrollo como en ejecutable PyInstaller.
    Usa sys._MEIPASS cuando estÃ¡ empacado.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return (base / rel_path).resolve()


def _has_display() -> bool:
    """En Linux/Unix, verifica si hay un servidor grÃ¡fico disponible."""
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True  # Windows normalmente tiene subsistema grÃ¡fico


class ExcelPrinterApp(tk.Tk):
    REPORT_DEFAULT_PRINTER = "Brother DCP-L5650DN series [b422002bd4a6]"
    LABEL_DEFAULT_PRINTER = "URBANO"

    def __init__(self):
        super().__init__()
        self.title("Exelcior Apolo | Centro de Despacho")
        self.configure(bg="#E7ECF3")
        self._apply_initial_geometry()

        init_db()
        from app.core.logger_eventos import log_evento
        log_evento("AplicaciÃ³n iniciada", nivel="info", accion="startup")

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
        self._active_print_context = "report"
        self._update_release_info = None
        self._update_download_thread = None
        self._update_button = None
        self._update_available = False
        self.current_version = get_local_version()
        self.status_var = tk.StringVar(value="Sistema operativo listo. Esperando carga o sincronizacion.")
        self.version_var = tk.StringVar(value=f"Version instalada: {self.current_version}")
        self.update_badge_var = tk.StringVar(value="Canal estable sin novedades")
        self.mode_description_var = tk.StringVar(value="Listados comerciales y documentos de venta")

        # âœ… Carga de config robusta
        try:
            config = load_config()
            if not isinstance(config, dict):
                logging.warning("[CONFIG] load_config no devolviÃ³ dict; usando {}")
                config = {}
        except Exception:
            logging.exception("[CONFIG] Error cargando configuraciÃ³n; usando {}")
            config = {}

        self.config_columns = config

        # ðŸŽ›ï¸ Selector de modo (Radiobutton para exclusividad)
        self.mode_var = tk.StringVar(value="listados")

        self._setup_styles()
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_status_bar()
        self.bind("<Configure>", self._on_root_resize)
        self._switch_print_context("report")
        self.after(2000, self._check_for_updates_async)

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
        Calcula un tamaÃ±o de ventana proporcional a la resoluciÃ³n disponible
        y centra la aplicaciÃ³n en pantalla, manteniendo un mÃ­nimo cÃ³modo.
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
        Ajusta elementos dependientes del tamaÃ±o cuando el usuario
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
        style.configure("TLabel", font=("Segoe UI", 10), background="#E7ECF3")
        style.configure("TCheckbutton", font=("Segoe UI", 10))
        style.configure("TRadiobutton", font=("Segoe UI", 10))
        style.configure(
            "Sidebar.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(14, 10),
            borderwidth=0,
            relief="flat",
            foreground="#DBE7FF",
            background="#132238",
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", "#1D3658"), ("disabled", "#0F1A2B")],
            foreground=[("active", "#FFFFFF"), ("disabled", "#627189")],
        )
        style.configure(
            "SidebarUpdate.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(14, 10),
            borderwidth=0,
            relief="flat",
            foreground="#FFF6DD",
            background="#B7791F",
        )
        style.map(
            "SidebarUpdate.TButton",
            background=[("active", "#D69E2E"), ("disabled", "#6D5525")],
            foreground=[("active", "#FFFFFF"), ("disabled", "#F2DFAE")],
        )
        style.configure("Mode.TLabelframe", padding=16, background="#FFFFFF")
        style.configure("Mode.TLabelframe.Label", font=("Segoe UI Semibold", 11), background="#FFFFFF", foreground="#243B53")
        style.configure("Status.TLabel", font=("Segoe UI", 10), padding=10, background="#102033", foreground="#E7EEF7")
        style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 30), foreground="#091E36", background="#F7FAFC")
        style.configure("CardSub.TLabel", font=("Segoe UI", 10), foreground="#516274", background="#F7FAFC")
        style.configure("HeroBadge.TLabel", font=("Segoe UI Semibold", 10), foreground="#FFF9EC", background="#9C6B17")
        style.configure("PanelTitle.TLabel", font=("Segoe UI Semibold", 12), foreground="#16324F", background="#FFFFFF")
        style.configure("MetricValue.TLabel", font=("Segoe UI Semibold", 16), foreground="#102A43", background="#FFFFFF")
        style.configure("MetricLabel.TLabel", font=("Segoe UI", 9), foreground="#6B7C93", background="#FFFFFF")

    def _add_sidebar_button(self, parent, text, cmd):
        b = ttk.Button(parent, text=text, command=cmd, style="Sidebar.TButton")
        b.pack(pady=6, fill="x", padx=12)
        self._sidebar_buttons.append(b)
        return b

    def _setup_sidebar(self):
        initial_width = getattr(self, "_initial_window_size", (1200, 800))[0]
        sidebar_width = max(220, int(initial_width * 0.18))
        sidebar = tk.Frame(self, bg="#0A1625", width=sidebar_width)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        brand = tk.Frame(sidebar, bg="#0F2237", bd=0, highlightthickness=1, highlightbackground="#1F3C5A")
        brand.pack(fill="x", padx=12, pady=(16, 14))
        tk.Label(brand, text="EXELCIOR", bg="#0F2237", fg="#D6E7FF",
                 font=("Segoe UI Semibold", 9), padx=14, pady=12).pack(anchor="w")
        tk.Label(brand, text="Apolo", bg="#0F2237", fg="#FFFFFF",
                 font=("Segoe UI Semibold", 18), padx=14).pack(anchor="w")
        tk.Label(
            brand,
            text="Centro de despacho, impresion y actualizaciones",
            bg="#0F2237",
            fg="#8FAECC",
            font=("Segoe UI", 9),
            padx=14,
        ).pack(anchor="w", pady=(2, 12))

        info_box = tk.Frame(sidebar, bg="#0A1625")
        info_box.pack(fill="x", padx=12, pady=(0, 12))
        tk.Label(info_box, textvariable=self.version_var, bg="#0A1625", fg="#A9BCD0", font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(info_box, textvariable=self.update_badge_var, bg="#0A1625", fg="#F4C86A", font=("Segoe UI Semibold", 9)).pack(anchor="w", pady=(4, 0))

        tk.Label(sidebar, text="Acciones disponibles", bg="#0A1625", fg="#6F89A8",
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=14, pady=(0, 10))

        self._add_sidebar_button(sidebar, "Seleccionar Excel", self._threaded_select_file)
        self._add_sidebar_button(sidebar, "Carga Automatica", self._threaded_auto_load)
        self._add_sidebar_button(sidebar, "Configurar Modo", self._open_config_menu)
        self._add_sidebar_button(sidebar, "Impresoras", self._abrir_admin_impresoras)
        self._add_sidebar_button(sidebar, "Ver Logs", self._view_logs)
        self._add_sidebar_button(sidebar, "Etiquetas", self._abrir_editor_etiquetas)
        self._add_sidebar_button(sidebar, "Codigos Postales", self._abrir_buscador_codigos_postales)
        self._add_sidebar_button(sidebar, "Sra Mary", self._abrir_sra_mary)
        self._add_sidebar_button(sidebar, "Inventario", lambda: InventarioView(self))
        self._add_sidebar_button(sidebar, "Vale de Consumo", self._abrir_vale_consumo)
        self._update_button = self._add_sidebar_button(sidebar, "Actualizar Sistema", self._download_and_install_update)
        self._update_button.configure(state=tk.DISABLED, style="SidebarUpdate.TButton")

        footer = tk.Frame(sidebar, bg="#0A1625")
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
        self.main_frame = tk.Frame(self, bg="#E7ECF3")
        self.main_frame.pack(side="left", fill="both", expand=True)
        self.main_frame.pack_propagate(False)

        hero = tk.Frame(self.main_frame, bg="#F7FAFC", bd=0, highlightthickness=1, highlightbackground="#D7E2EF")
        hero.pack(fill="x", padx=24, pady=(24, 12))

        ttk.Label(hero, text="Centro de Despacho Exelcior", style="CardTitle.TLabel", anchor="center").pack(
            pady=(22, 6), padx=24, fill="x"
        )
        ttk.Label(
            hero,
            text="Una consola unificada para preparar archivos, validar salidas y mantener cada puesto sincronizado.",
            style="CardSub.TLabel",
            anchor="center",
        ).pack(pady=(0, 12), padx=24, fill="x")
        ttk.Label(hero, text="Canal operativo + releases automÃ¡ticos", style="HeroBadge.TLabel", anchor="center").pack(
            pady=(0, 18), ipadx=12, ipady=4
        )
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

        summary_row = tk.Frame(self.main_frame, bg="#E7ECF3")
        summary_row.pack(fill="x", padx=24, pady=(0, 12))
        self._build_metric_card(
            summary_row,
            "Operacion activa",
            self.mode_var.get().capitalize(),
            self.mode_description_var,
            "#16324F",
        ).pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._build_metric_card(
            summary_row,
            "Version de cliente",
            self.current_version,
            self.update_badge_var,
            "#285E61",
        ).pack(side="left", fill="both", expand=True, padx=8)
        self._build_metric_card(
            summary_row,
            "Pulso del sistema",
            "Listo para procesar",
            self.status_var,
            "#8B5E34",
        ).pack(side="left", fill="both", expand=True, padx=(8, 0))

        showcase = tk.Frame(self.main_frame, bg="#E7ECF3")
        showcase.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        showcase.columnconfigure(0, weight=3)
        showcase.columnconfigure(1, weight=2)
        showcase.rowconfigure(0, weight=1)

        visual_panel = tk.Frame(showcase, bg="#FFFFFF", bd=0, highlightthickness=1, highlightbackground="#D7E2EF")
        visual_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        side_panel = tk.Frame(showcase, bg="#FFFFFF", bd=0, highlightthickness=1, highlightbackground="#D7E2EF")
        side_panel.grid(row=0, column=1, sticky="nsew")

        # -------- LOGO / identidad --------
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
                img.thumbnail((220, 220), Image.LANCZOS)
                self._logo_image = ImageTk.PhotoImage(img)  # guardar referencia
                tk.Label(visual_panel, image=self._logo_image, bg="#FFFFFF").pack(padx=20, pady=(28, 14))
            else:
                tk.Label(visual_panel, text="[Logo no encontrado]", bg="#FFFFFF", fg="#c00").pack(pady=18)
        except Exception as e:
            tk.Label(visual_panel, text=f"[Error cargando logo: {e}]", bg="#FFFFFF", fg="#c00").pack(pady=18)

        ttk.Label(visual_panel, text="Recorrido recomendado", style="PanelTitle.TLabel").pack(anchor="w", padx=24, pady=(8, 4))
        for step in (
            "1. Selecciona el canal operativo correcto para la carga",
            "2. Carga manual o automÃ¡tica del Excel",
            "3. Revisa la vista previa y valida impresoras antes de emitir",
            "4. Publica releases y replica cambios a todos los puestos",
        ):
            tk.Label(visual_panel, text=step, bg="#FFFFFF", fg="#51606F", font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=4)

        ttk.Label(side_panel, text="Salud operativa", style="PanelTitle.TLabel").pack(anchor="w", padx=20, pady=(22, 10))
        self._build_info_row(side_panel, "Canal de actualizacion", self.update_badge_var).pack(fill="x", padx=20, pady=6)
        self._build_info_row(side_panel, "Version local", self.version_var).pack(fill="x", padx=20, pady=6)
        self._build_info_row(side_panel, "Operacion", self.mode_description_var).pack(fill="x", padx=20, pady=6)
        self._build_info_row(side_panel, "Estado en vivo", self.status_var).pack(fill="x", padx=20, pady=6)

        self._content_spacer = tk.Frame(self.main_frame, bg="#E7ECF3")
        self._content_spacer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def _setup_status_bar(self):
        status_frame = tk.Frame(self, bg="#102033")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W, style="Status.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    def _build_metric_card(self, parent, title: str, value: str, detail_var: tk.StringVar, accent: str):
        card = tk.Frame(parent, bg="#FFFFFF", bd=0, highlightthickness=1, highlightbackground="#D7E2EF")
        header = tk.Frame(card, bg=accent, height=6)
        header.pack(fill="x")
        body = tk.Frame(card, bg="#FFFFFF")
        body.pack(fill="both", expand=True, padx=16, pady=14)
        ttk.Label(body, text=title, style="MetricLabel.TLabel").pack(anchor="w")
        ttk.Label(body, text=value, style="MetricValue.TLabel").pack(anchor="w", pady=(2, 6))
        tk.Label(body, textvariable=detail_var, bg="#FFFFFF", fg="#66788A", font=("Segoe UI", 9), wraplength=240, justify="left").pack(anchor="w")
        return card

    def _build_info_row(self, parent, title: str, value_var: tk.StringVar):
        row = tk.Frame(parent, bg="#F8FBFD", bd=0, highlightthickness=1, highlightbackground="#E2E8F0")
        tk.Label(row, text=title, bg="#F8FBFD", fg="#34495E", font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(row, textvariable=value_var, bg="#F8FBFD", fg="#637381", font=("Segoe UI", 9), wraplength=260, justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        return row

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

    def _check_for_updates_async(self) -> None:
        if getattr(self, "_update_check_started", False):
            return
        self._update_check_started = True
        thread = threading.Thread(target=self._check_for_updates_worker, daemon=True)
        thread.start()

    def _check_for_updates_worker(self) -> None:
        try:
            current_version = get_local_version()
            payload = fetch_latest_release()
            release_info = parse_release_info(payload or {})
            if not release_info:
                logging.info("No hay release publicable con instalador para auto-update.")
                return
            if not is_newer_version(release_info["version"], current_version):
                logging.info(
                    "Version actual al dia. Local=%s Remota=%s",
                    current_version,
                    release_info["version"],
                )
                return
            self._update_release_info = release_info
            if self._ui_alive():
                self.after(0, self._mark_update_available)
        except Exception as e:
            logging.info("No se pudo comprobar actualizaciones: %s", e)

    def _mark_update_available(self) -> None:
        release_info = self._update_release_info
        if not release_info or not self._ui_alive():
            return
        self._update_available = True
        self.update_badge_var.set(f"Disponible: {release_info['version']}")
        if self._update_button is not None:
            self._update_button.configure(state=tk.NORMAL, text=f"Actualizar ({release_info['version']})")
        self._update_status(f"Actualizacion disponible: {release_info['version']}")

    def _download_and_install_update(self) -> None:
        release_info = self._update_release_info
        if not release_info:
            self.safe_messagebox("info", "Actualizacion", "No hay una actualizacion disponible en este momento.")
            return
        current_version = get_local_version()
        wants_update = messagebox.askyesno(
            "Actualizacion disponible",
            (
                f"Hay una nueva version disponible.\n\n"
                f"Version actual: {current_version}\n"
                f"Ultima version: {release_info['version']}\n\n"
                f"Se descargara el instalador oficial desde GitHub Releases."
            ),
            parent=self,
        )
        if not wants_update:
            return
        if self._update_button is not None:
            self._update_button.configure(state=tk.DISABLED, text="Descargando actualizacion...")
        self.update_badge_var.set(f"Descargando version {release_info['version']}")
        self._update_status(f"Descargando actualizacion {release_info['version']}...")
        self._update_download_thread = start_update_download(
            release_info=release_info,
            on_ready=lambda installer_path: self.after(0, lambda: self._finish_update_download(installer_path)),
            on_error=lambda exc: self.after(0, lambda: self._handle_update_error(exc)),
        )

    def _finish_update_download(self, installer_path: Path) -> None:
        try:
            launch_installer(installer_path)
            self._update_status("Instalador lanzado. Cerrando aplicacion...")
            self.after(500, self._on_close)
        except Exception as exc:
            self._handle_update_error(exc)

    def _handle_update_error(self, exc: Exception) -> None:
        logging.exception("Error durante la actualizacion")
        self._update_status("No se pudo completar la actualizacion.")
        if self._update_button is not None and self._update_available and self._update_release_info:
            self._update_button.configure(
                state=tk.NORMAL,
                text=f"Actualizar ({self._update_release_info['version']})",
            )
        if self._update_release_info:
            self.update_badge_var.set(f"Disponible: {self._update_release_info['version']}")
        self.safe_messagebox(
            "error",
            "Actualizacion",
            f"No se pudo descargar o iniciar la actualizacion:\n{exc}",
        )

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
        descriptions = {
            "listados": "Listados comerciales y documentos de venta",
            "fedex": "Guias y trazabilidad de despacho FedEx",
            "urbano": "Preparacion de planillas para operador Urbano",
        }
        self.mode_description_var.set(descriptions.get(modo_seleccionado, modo_seleccionado.capitalize()))
        self._refresh_mode_buttons()
        self._switch_print_context("report")
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
        # Reportes: usa impresora por modo si existe, si no toma la general.
        report_printer = ""
        try:
            latest_cfg = load_config()
            if isinstance(latest_cfg, dict):
                self.config_columns = latest_cfg
        except Exception:
            pass
        if isinstance(self.config_columns, dict):
            mode_printers = self.config_columns.get("mode_printers", {})
            if isinstance(mode_printers, dict):
                mode_specific = mode_printers.get((self.mode or "").strip().lower(), "")
                if isinstance(mode_specific, str) and mode_specific.strip():
                    report_printer = mode_specific.strip()
            report_printer = (
                report_printer
                or self.config_columns.get("report_printer_name")
                or self.config_columns.get("paper_printer_name")
                or self.config_columns.get("default_printer")
                or (self.config_columns.get("paths", {}) or {}).get("default_printer")
                or self.REPORT_DEFAULT_PRINTER
            )
        self._set_windows_default_printer(str(report_printer))

    def _apply_default_printer_for_labels(self) -> None:
        # Etiquetas: usar la configuraciÃ³n del editor de etiquetas.
        # (archivo excel_printer_config.json, donde se guarda la etiquetadora elegida)
        label_cfg = {}
        try:
            label_cfg = cargar_config_etiquetas() or {}
        except Exception:
            label_cfg = {}
        label_printer = (
            (self.config_columns.get("label_printer_name") if isinstance(self.config_columns, dict) else "")
            or (self.config_columns.get("printer_name") if isinstance(self.config_columns, dict) else "")
            or label_cfg.get("label_printer_name")
            or label_cfg.get("printer_name")
            or self.LABEL_DEFAULT_PRINTER
        )
        self._set_windows_default_printer(str(label_printer))

    def _switch_print_context(self, context: str) -> None:
        """
        Cambia automÃ¡ticamente la impresora default segÃºn el contexto activo:
        - report: listados/fedex/urbano
        - labels: editor/impresiÃ³n de etiquetas
        """
        ctx = (context or "").strip().lower()
        if ctx not in ("report", "labels"):
            return
        if ctx == self._active_print_context:
            # Igual se reaplica para sincronizar si el usuario cambiÃ³ impresoras fuera de la app.
            pass
        if ctx == "labels":
            self._apply_default_printer_for_labels()
        else:
            self._apply_default_printer_for_report_mode()
        self._active_print_context = ctx

    def _abrir_buscador_codigos_postales(self):
        from app.gui.buscador_codigos_postales import BuscadorCodigosPostales
        BuscadorCodigosPostales(self)

    def _abrir_admin_impresoras(self):
        dlg = PrinterAdminDialog(self)
        self.wait_window(dlg)
        try:
            latest_cfg = load_config()
            if isinstance(latest_cfg, dict):
                self.config_columns = latest_cfg
        except Exception:
            pass
        self._switch_print_context("report")

    def _abrir_sra_mary(self):
        SraMaryView(self)

    def _abrir_vale_consumo(self):
        """
        Abre la app de Vale de Consumo (Bioplates) en una ventana separada.

        - En desarrollo: lanza vale_consumo/run_app.py con el intÃ©rprete actual.
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
                    "No se encontrÃ³ 'ValeConsumoBioplates.exe'.\n"
                    "Copia el ejecutable de vales junto a ExelciorApolo.exe "
                    "o dentro de una carpeta 'vale_consumo' y vuelve a intentarlo.",
                )
                return

            script_path = (ROOT_DIR / "vale_consumo" / "run_app.py").resolve()
            if not script_path.exists():
                self.safe_messagebox(
                    "error",
                    "Vale de Consumo",
                    "No se encontrÃ³ 'vale_consumo/run_app.py' en la carpeta del proyecto.",
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
            self.safe_messagebox("error", "Archivo no vÃ¡lido", err)
            log_evento(f"Archivo no vÃ¡lido seleccionado: {path}", nivel="warning", accion="seleccion_archivo")
            return
        # Primera carga manual: usa la misma carpeta base para todos los modos principales.
        base_folder = Path(path).parent
        for m in ("listados", "fedex", "urbano"):
            set_carpeta_descarga_personalizada(base_folder, m)
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
        self._update_status("Buscando archivo mÃ¡s reciente...")
        try:
            archivo, estado = find_latest_file_by_mode(self.mode)
            if estado == "ok" and archivo:
                valido, msg = validate_file(str(archivo))
                if not valido:
                    self._update_status(f"âš ï¸ Archivo mÃ¡s reciente invÃ¡lido: {msg}")
                    self.safe_messagebox("error", "Archivo no vÃ¡lido", msg)
                    return
                self._update_status(f"âœ… Cargado: {archivo.name}")
                self._process_file(str(archivo))
            elif estado == "no_match":
                self._update_status("âš ï¸ No se encontraron archivos compatibles.")
                self.safe_messagebox("warning", "Sin coincidencias", f"No hay archivos vÃ¡lidos para el modo '{self.mode}'")
            elif estado == "empty_folder":
                self._update_status("ðŸ“‚ Carpeta vacÃ­a o inexistente.")
                self.safe_messagebox("error", "Carpeta vacÃ­a", "La carpeta de descargas estÃ¡ vacÃ­a o no existe.")
            else:
                self._update_status("âŒ Error en la autocarga.")
        except Exception as e:
            logging.error(f"Error en carga automÃ¡tica: {e}")
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

    # ---------------- ImpresiÃ³n ----------------

    def _threaded_print(self):
        if self.processing or self.transformed_df is None or self.transformed_df.empty:
            self.safe_messagebox("error", "Error", "Debe cargar un archivo vÃ¡lido primero.")
            return
        # Refuerzo: antes de imprimir reportes, aplicar siempre default de informes.
        if self.mode in ("listados", "fedex", "urbano"):
            self._switch_print_context("report")
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
            # Imprime exactamente lo que estÃ¡ en la vista previa/CRUD
            print_document(self.mode, self.transformed_df, self.config_columns, None)
            save_print_history(
                archivo=f"{self.mode}_impresion.xlsx",
                observacion=f"ImpresiÃ³n realizada en modo '{self.mode}'"
            )
            self.df = None
            self.transformed_df = None
        except Exception as e:
            logging.error(f"Error en impresiÃ³n: {e}")
            capturar_log_bod1(f"Error al imprimir: {e}", "error")
            if self._ui_alive():
                msg = f"Error al imprimir:\n{e}"
                self.after(0, lambda m=msg: self.safe_messagebox("error", "Error", m))
            raise

    # ---------------- ConfiguraciÃ³n ----------------

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
            self._switch_print_context("labels")
            win = crear_editor_etiqueta(parent=self)
            if win is not None:
                restored = {"done": False}

                def _restore_report_printer_once() -> None:
                    if restored["done"]:
                        return
                    restored["done"] = True
                    self._switch_print_context("report")

                def _on_close_labels():
                    try:
                        win.destroy()
                    finally:
                        _restore_report_printer_once()

                win.protocol("WM_DELETE_WINDOW", _on_close_labels)
                win.bind("<Destroy>", lambda e: _restore_report_printer_once() if e.widget is win else None)
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

        # Prioriza el log mÃ¡s reciente con contenido para evitar abrir archivos vacÃ­os.
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

        ttk.Button(win, text="ðŸ” Refrescar Log", command=cargar_log).pack(pady=5)
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
    # Si no hay servidor grÃ¡fico, informa y aborta con cÃ³digo claro
    if not _has_display():
        logging.error("No se detectÃ³ DISPLAY/servidor grÃ¡fico. La interfaz Tkinter requiere entorno grÃ¡fico.")
        print("Error: No se detectÃ³ entorno grÃ¡fico (DISPLAY/Wayland).")
        sys.exit(2)

    try:
        run_app()
    except Exception as e:
        logging.exception("Error fatal en la aplicaciÃ³n")
        try:
            # Solo intentes messagebox si hay display
            if _has_display():
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error crÃ­tico", f"OcurriÃ³ un error fatal:\n{e}")
                root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()



