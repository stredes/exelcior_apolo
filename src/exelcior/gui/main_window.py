"""
Ventana principal de la interfaz gráfica de Exelcior Apolo.

Implementa una interfaz moderna y intuitiva con diseño responsive
y componentes bien organizados.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Dict, Any
import threading
from datetime import datetime

from ..constants import GUI_CONFIG, OPERATION_MODES, MESSAGES
from ..config import config_manager
from ..core import excel_processor, autoloader
from ..printer import print_manager
from ..database import database_manager
from ..utils import get_logger, ExelciorError, FileProcessingError

logger = get_logger("exelcior.gui.main")


class MainWindow:
    """
    Ventana principal de la aplicación.
    
    Implementa una interfaz moderna con sidebar, área principal
    y componentes bien organizados.
    """

    def __init__(self, root: tk.Tk):
        """
        Inicializa la ventana principal.
        
        Args:
            root: Widget raíz de Tkinter
        """
        self.root = root
        self.current_file: Optional[Path] = None
        self.current_dataframe = None
        self.current_mode = config_manager.user.default_mode
        
        self._setup_styles()
        self._create_widgets()
        self._setup_layout()
        self._bind_events()
        
        # Cargar archivo automáticamente si está habilitado
        if config_manager.user.auto_load_enabled:
            self._auto_load_file()

    def _setup_styles(self) -> None:
        """Configura los estilos de la interfaz."""
        self.style = ttk.Style()
        
        # Configurar colores
        colors = GUI_CONFIG["colors"]
        
        # Estilo para botones principales
        self.style.configure(
            "Primary.TButton",
            background=colors["accent"],
            foreground="white",
            font=(GUI_CONFIG["font_family"], GUI_CONFIG["font_size"], "bold")
        )
        
        # Estilo para botones de éxito
        self.style.configure(
            "Success.TButton",
            background=colors["success"],
            foreground="white"
        )
        
        # Estilo para botones de advertencia
        self.style.configure(
            "Warning.TButton",
            background=colors["warning"],
            foreground="white"
        )
        
        # Estilo para frames principales
        self.style.configure(
            "Card.TFrame",
            background=colors["secondary"],
            relief="solid",
            borderwidth=1
        )

    def _create_widgets(self) -> None:
        """Crea todos los widgets de la interfaz."""
        # Frame principal
        self.main_frame = ttk.Frame(self.root)
        
        # Sidebar
        self._create_sidebar()
        
        # Área principal
        self._create_main_area()
        
        # Barra de estado
        self._create_status_bar()

    def _create_sidebar(self) -> None:
        """Crea el sidebar con controles principales."""
        self.sidebar = ttk.Frame(self.main_frame, style="Card.TFrame", width=250)
        self.sidebar.pack_propagate(False)
        
        # Título del sidebar
        title_label = ttk.Label(
            self.sidebar,
            text="Exelcior Apolo",
            font=(GUI_CONFIG["font_family"], 16, "bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Sección de archivo
        self._create_file_section()
        
        # Sección de modo
        self._create_mode_section()
        
        # Sección de acciones
        self._create_actions_section()
        
        # Sección de configuración
        self._create_config_section()

    def _create_file_section(self) -> None:
        """Crea la sección de manejo de archivos."""
        file_frame = ttk.LabelFrame(self.sidebar, text="Archivo", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        # Botón seleccionar archivo
        self.select_file_btn = ttk.Button(
            file_frame,
            text="📁 Seleccionar Archivo",
            command=self._select_file,
            style="Primary.TButton"
        )
        self.select_file_btn.pack(fill="x", pady=2)
        
        # Botón auto-cargar
        self.auto_load_btn = ttk.Button(
            file_frame,
            text="🔄 Auto-cargar",
            command=self._auto_load_file
        )
        self.auto_load_btn.pack(fill="x", pady=2)
        
        # Label del archivo actual
        self.file_label = ttk.Label(
            file_frame,
            text="Ningún archivo seleccionado",
            wraplength=200,
            font=(GUI_CONFIG["font_family"], 9)
        )
        self.file_label.pack(fill="x", pady=5)

    def _create_mode_section(self) -> None:
        """Crea la sección de selección de modo."""
        mode_frame = ttk.LabelFrame(self.sidebar, text="Modo de Operación", padding=10)
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        # Variable para el modo
        self.mode_var = tk.StringVar(value=self.current_mode)
        
        # Radio buttons para cada modo
        for mode_key, mode_config in OPERATION_MODES.items():
            radio = ttk.Radiobutton(
                mode_frame,
                text=mode_config["name"],
                variable=self.mode_var,
                value=mode_key,
                command=self._on_mode_change
            )
            radio.pack(anchor="w", pady=2)
        
        # Descripción del modo actual
        self.mode_desc_label = ttk.Label(
            mode_frame,
            text=OPERATION_MODES[self.current_mode]["description"],
            wraplength=200,
            font=(GUI_CONFIG["font_family"], 8),
            foreground="gray"
        )
        self.mode_desc_label.pack(fill="x", pady=5)

    def _create_actions_section(self) -> None:
        """Crea la sección de acciones principales."""
        actions_frame = ttk.LabelFrame(self.sidebar, text="Acciones", padding=10)
        actions_frame.pack(fill="x", padx=10, pady=5)
        
        # Botón procesar
        self.process_btn = ttk.Button(
            actions_frame,
            text="⚡ Procesar",
            command=self._process_file,
            style="Success.TButton",
            state="disabled"
        )
        self.process_btn.pack(fill="x", pady=2)
        
        # Botón exportar PDF
        self.export_pdf_btn = ttk.Button(
            actions_frame,
            text="📄 Exportar PDF",
            command=self._export_pdf,
            state="disabled"
        )
        self.export_pdf_btn.pack(fill="x", pady=2)
        
        # Botón imprimir
        self.print_btn = ttk.Button(
            actions_frame,
            text="🖨️ Imprimir",
            command=self._print_document,
            state="disabled"
        )
        self.print_btn.pack(fill="x", pady=2)

    def _create_config_section(self) -> None:
        """Crea la sección de configuración."""
        config_frame = ttk.LabelFrame(self.sidebar, text="Configuración", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # Botón configuración
        config_btn = ttk.Button(
            config_frame,
            text="⚙️ Configurar",
            command=self._open_config
        )
        config_btn.pack(fill="x", pady=2)
        
        # Botón historial
        history_btn = ttk.Button(
            config_frame,
            text="📊 Historial",
            command=self._open_history
        )
        history_btn.pack(fill="x", pady=2)

    def _create_main_area(self) -> None:
        """Crea el área principal de contenido."""
        self.main_area = ttk.Frame(self.main_frame)
        
        # Notebook para pestañas
        self.notebook = ttk.Notebook(self.main_area)
        
        # Pestaña de datos
        self._create_data_tab()
        
        # Pestaña de información
        self._create_info_tab()
        
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_data_tab(self) -> None:
        """Crea la pestaña de visualización de datos."""
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="📊 Datos")
        
        # Treeview para mostrar datos
        self.tree_frame = ttk.Frame(self.data_frame)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical")
        h_scrollbar = ttk.Scrollbar(self.tree_frame, orient="horizontal")
        
        # Treeview
        self.data_tree = ttk.Treeview(
            self.tree_frame,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        v_scrollbar.config(command=self.data_tree.yview)
        h_scrollbar.config(command=self.data_tree.xview)
        
        # Layout de scrollbars y treeview
        self.data_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Label de información
        self.data_info_label = ttk.Label(
            self.data_frame,
            text="Seleccione un archivo para ver los datos",
            font=(GUI_CONFIG["font_family"], 10)
        )
        self.data_info_label.pack(pady=10)

    def _create_info_tab(self) -> None:
        """Crea la pestaña de información del archivo."""
        self.info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.info_frame, text="ℹ️ Información")
        
        # Text widget para información
        self.info_text = tk.Text(
            self.info_frame,
            wrap="word",
            font=(GUI_CONFIG["font_family"], 10),
            state="disabled"
        )
        
        info_scrollbar = ttk.Scrollbar(self.info_frame, orient="vertical")
        info_scrollbar.config(command=self.info_text.yview)
        self.info_text.config(yscrollcommand=info_scrollbar.set)
        
        self.info_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        info_scrollbar.pack(side="right", fill="y", pady=10)

    def _create_status_bar(self) -> None:
        """Crea la barra de estado."""
        self.status_frame = ttk.Frame(self.root)
        
        # Label de estado
        self.status_label = ttk.Label(
            self.status_frame,
            text="Listo",
            font=(GUI_CONFIG["font_family"], 9)
        )
        self.status_label.pack(side="left", padx=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.status_frame,
            variable=self.progress_var,
            mode="determinate"
        )
        self.progress_bar.pack(side="right", padx=10, pady=5, fill="x", expand=True)

    def _setup_layout(self) -> None:
        """Configura el layout principal."""
        # Configurar grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Pack frames principales
        self.main_frame.pack(fill="both", expand=True)
        
        # Layout del main_frame
        self.sidebar.pack(side="left", fill="y")
        self.main_area.pack(side="right", fill="both", expand=True)
        
        # Status bar al final
        self.status_frame.pack(side="bottom", fill="x")

    def _bind_events(self) -> None:
        """Vincula eventos de la interfaz."""
        # Drag and drop (simplificado)
        self.root.bind("<Button-1>", self._on_click)
        
        # Atajos de teclado
        self.root.bind("<Control-o>", lambda e: self._select_file())
        self.root.bind("<Control-p>", lambda e: self._process_file())
        self.root.bind("<F5>", lambda e: self._auto_load_file())

    def _select_file(self) -> None:
        """Abre diálogo para seleccionar archivo."""
        try:
            filetypes = [
                ("Archivos Excel", "*.xlsx *.xls *.xlsm *.xlsb"),
                ("Archivos CSV", "*.csv"),
                ("Todos los archivos", "*.*")
            ]
            
            initial_dir = config_manager.get_download_path(self.current_mode)
            
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo",
                initialdir=str(initial_dir),
                filetypes=filetypes
            )
            
            if file_path:
                self._load_file(Path(file_path))
                
        except Exception as e:
            logger.error(f"Error al seleccionar archivo: {e}")
            self._show_error("Error al seleccionar archivo", str(e))

    def _auto_load_file(self) -> None:
        """Carga automáticamente el archivo más reciente."""
        try:
            self._update_status("Buscando archivo más reciente...")
            
            # Ejecutar en hilo separado para no bloquear UI
            def auto_load_thread():
                try:
                    file_path, status = autoloader.find_latest_file(self.current_mode)
                    
                    if status == "ok" and file_path:
                        # Actualizar UI en hilo principal
                        self.root.after(0, lambda: self._load_file(file_path))
                    else:
                        message = {
                            "no_match": "No se encontraron archivos para el modo actual",
                            "empty_folder": "No hay archivos en el directorio",
                            "error": "Error en la búsqueda automática"
                        }.get(status, "No se pudo cargar archivo automáticamente")
                        
                        self.root.after(0, lambda: self._update_status(message))
                        
                except Exception as e:
                    logger.error(f"Error en auto-carga: {e}")
                    self.root.after(0, lambda: self._update_status("Error en auto-carga"))
            
            threading.Thread(target=auto_load_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error al iniciar auto-carga: {e}")
            self._update_status("Error al iniciar auto-carga")

    def _load_file(self, file_path: Path) -> None:
        """
        Carga un archivo específico.
        
        Args:
            file_path: Ruta del archivo a cargar
        """
        try:
            self._update_status(f"Cargando {file_path.name}...")
            self.progress_var.set(25)
            
            # Cargar archivo
            df = excel_processor.load_file(file_path, self.current_mode, max_rows=1000)
            
            self.progress_var.set(50)
            
            # Actualizar estado
            self.current_file = file_path
            self.current_dataframe = df
            
            # Actualizar UI
            self._update_file_display()
            self._update_data_display()
            self._update_info_display()
            
            # Habilitar botones
            self.process_btn.config(state="normal")
            
            self.progress_var.set(100)
            self._update_status(f"Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
            
            # Añadir a archivos recientes
            config_manager.add_recent_file(str(file_path), self.current_mode)
            
            # Limpiar progress bar después de un momento
            self.root.after(2000, lambda: self.progress_var.set(0))
            
        except FileProcessingError as e:
            logger.error(f"Error al cargar archivo: {e}")
            self._show_error("Error al cargar archivo", e.message)
            self._reset_file_state()
        except Exception as e:
            logger.error(f"Error inesperado al cargar archivo: {e}")
            self._show_error("Error inesperado", str(e))
            self._reset_file_state()

    def _process_file(self) -> None:
        """Procesa el archivo actual."""
        if not self.current_dataframe is not None:
            self._show_warning("No hay archivo cargado para procesar")
            return
        
        try:
            self._update_status("Procesando archivo...")
            self.progress_var.set(25)
            
            start_time = datetime.now()
            
            # Transformar datos
            processed_df, total = excel_processor.transform_data(
                self.current_dataframe, 
                self.current_mode
            )
            
            self.progress_var.set(75)
            
            # Actualizar datos mostrados
            self.current_dataframe = processed_df
            self._update_data_display()
            
            # Habilitar botones de exportación
            self.export_pdf_btn.config(state="normal")
            self.print_btn.config(state="normal")
            
            # Calcular tiempo de procesamiento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Guardar en historial
            database_manager.save_file_history(
                file_path=self.current_file,
                mode=self.current_mode,
                file_size=self.current_file.stat().st_size,
                rows_processed=len(processed_df),
                processing_time=processing_time,
                success=True
            )
            
            self.progress_var.set(100)
            
            # Mensaje de éxito
            message = f"Procesamiento completado: {len(processed_df)} registros"
            if total is not None:
                message += f", Total: {total}"
            
            self._update_status(message)
            self._show_success("Procesamiento completado", message)
            
            # Limpiar progress bar
            self.root.after(2000, lambda: self.progress_var.set(0))
            
        except Exception as e:
            logger.error(f"Error al procesar archivo: {e}")
            self._show_error("Error en procesamiento", str(e))
            self.progress_var.set(0)

    def _export_pdf(self) -> None:
        """Exporta los datos a PDF."""
        if self.current_dataframe is None:
            self._show_warning("No hay datos para exportar")
            return
        
        try:
            self._update_status("Exportando a PDF...")
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.current_mode}_{timestamp}"
            
            # Exportar
            result = print_manager.print_dataframe(
                self.current_dataframe,
                mode="pdf",
                filename=filename,
                title=f"Reporte {OPERATION_MODES[self.current_mode]['name']}"
            )
            
            if result["success"]:
                self._update_status(f"PDF exportado: {result['output_path']}")
                self._show_success("Exportación exitosa", result["message"])
            else:
                self._show_error("Error en exportación", result["message"])
                
        except Exception as e:
            logger.error(f"Error al exportar PDF: {e}")
            self._show_error("Error en exportación", str(e))

    def _print_document(self) -> None:
        """Imprime el documento actual."""
        if self.current_dataframe is None:
            self._show_warning("No hay datos para imprimir")
            return
        
        # Mostrar diálogo de opciones de impresión
        self._show_print_dialog()

    def _show_print_dialog(self) -> None:
        """Muestra diálogo de opciones de impresión."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Opciones de Impresión")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar diálogo
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # Contenido del diálogo
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = ttk.Label(
            main_frame,
            text="Seleccione tipo de impresión:",
            font=(GUI_CONFIG["font_family"], 12, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Opciones
        ttk.Button(
            main_frame,
            text="🖨️ Impresora del Sistema",
            command=lambda: self._execute_print("system", dialog),
            style="Primary.TButton"
        ).pack(fill="x", pady=5)
        
        ttk.Button(
            main_frame,
            text="🏷️ Impresora Zebra",
            command=lambda: self._execute_print("zebra", dialog)
        ).pack(fill="x", pady=5)
        
        ttk.Button(
            main_frame,
            text="📄 Solo generar PDF",
            command=lambda: self._execute_print("pdf", dialog)
        ).pack(fill="x", pady=5)
        
        # Botón cancelar
        ttk.Button(
            main_frame,
            text="Cancelar",
            command=dialog.destroy
        ).pack(pady=(20, 0))

    def _execute_print(self, print_mode: str, dialog: tk.Toplevel) -> None:
        """
        Ejecuta la impresión en el modo especificado.
        
        Args:
            print_mode: Modo de impresión
            dialog: Diálogo a cerrar
        """
        dialog.destroy()
        
        try:
            self._update_status(f"Imprimiendo en modo {print_mode}...")
            
            result = print_manager.print_dataframe(
                self.current_dataframe,
                mode=print_mode
            )
            
            if result["success"]:
                self._update_status("Impresión completada")
                self._show_success("Impresión exitosa", result["message"])
            else:
                self._show_error("Error en impresión", result["message"])
                
        except Exception as e:
            logger.error(f"Error al imprimir: {e}")
            self._show_error("Error en impresión", str(e))

    def _on_mode_change(self) -> None:
        """Maneja el cambio de modo de operación."""
        new_mode = self.mode_var.get()
        if new_mode != self.current_mode:
            self.current_mode = new_mode
            
            # Actualizar descripción
            self.mode_desc_label.config(
                text=OPERATION_MODES[new_mode]["description"]
            )
            
            # Guardar en configuración
            config_manager.update_user_config(default_mode=new_mode)
            
            # Recargar archivo si hay uno cargado
            if self.current_file:
                self._load_file(self.current_file)
            
            logger.info(f"Modo cambiado a: {new_mode}")

    def _update_file_display(self) -> None:
        """Actualiza la visualización del archivo actual."""
        if self.current_file:
            self.file_label.config(text=f"📄 {self.current_file.name}")
        else:
            self.file_label.config(text="Ningún archivo seleccionado")

    def _update_data_display(self) -> None:
        """Actualiza la visualización de datos en el treeview."""
        # Limpiar treeview
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        
        if self.current_dataframe is None:
            self.data_info_label.config(text="No hay datos para mostrar")
            return
        
        df = self.current_dataframe
        
        # Configurar columnas
        columns = list(df.columns)
        self.data_tree["columns"] = columns
        self.data_tree["show"] = "headings"
        
        # Configurar encabezados
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100, minwidth=50)
        
        # Insertar datos (máximo 100 filas para rendimiento)
        max_rows = min(100, len(df))
        for i in range(max_rows):
            values = [str(df.iloc[i][col]) for col in columns]
            self.data_tree.insert("", "end", values=values)
        
        # Actualizar información
        info_text = f"Mostrando {max_rows} de {len(df)} filas, {len(columns)} columnas"
        if max_rows < len(df):
            info_text += f" (limitado a {max_rows} filas para rendimiento)"
        
        self.data_info_label.config(text=info_text)

    def _update_info_display(self) -> None:
        """Actualiza la información del archivo."""
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        
        if self.current_file and self.current_dataframe is not None:
            info = excel_processor.get_file_info(self.current_file)
            df = self.current_dataframe
            
            info_text = f"""INFORMACIÓN DEL ARCHIVO

Nombre: {info.get('name', 'N/A')}
Tamaño: {info.get('size_mb', 0):.2f} MB
Formato: {info.get('extension', 'N/A')}
Modo: {OPERATION_MODES[self.current_mode]['name']}

DATOS CARGADOS

Filas: {len(df):,}
Columnas: {len(df.columns)}
Memoria: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB

COLUMNAS

{chr(10).join([f"• {col}" for col in df.columns])}

ESTADÍSTICAS

{df.describe(include='all').to_string() if len(df) > 0 else 'No hay datos numéricos'}
"""
            
            self.info_text.insert(1.0, info_text)
        
        self.info_text.config(state="disabled")

    def _update_status(self, message: str) -> None:
        """
        Actualiza el mensaje de estado.
        
        Args:
            message: Mensaje a mostrar
        """
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def _reset_file_state(self) -> None:
        """Resetea el estado del archivo actual."""
        self.current_file = None
        self.current_dataframe = None
        
        # Deshabilitar botones
        self.process_btn.config(state="disabled")
        self.export_pdf_btn.config(state="disabled")
        self.print_btn.config(state="disabled")
        
        # Limpiar displays
        self._update_file_display()
        self._update_data_display()
        self._update_info_display()
        
        # Limpiar progress bar
        self.progress_var.set(0)

    def _show_success(self, title: str, message: str) -> None:
        """Muestra mensaje de éxito."""
        messagebox.showinfo(title, message)

    def _show_warning(self, message: str) -> None:
        """Muestra mensaje de advertencia."""
        messagebox.showwarning("Advertencia", message)

    def _show_error(self, title: str, message: str) -> None:
        """Muestra mensaje de error."""
        messagebox.showerror(title, message)

    def _open_config(self) -> None:
        """Abre ventana de configuración."""
        # TODO: Implementar ventana de configuración
        self._show_warning("Ventana de configuración en desarrollo")

    def _open_history(self) -> None:
        """Abre ventana de historial."""
        # TODO: Implementar ventana de historial
        self._show_warning("Ventana de historial en desarrollo")

    def _on_click(self, event) -> None:
        """Maneja clicks en la ventana."""
        # Placeholder para funcionalidad futura
        pass

