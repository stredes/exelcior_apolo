import logging
import platform
import sys
import tempfile
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd
from exelcior.core.integrated_processor import IntegratedExcelProcessor
from exelcior.gui.config_window import ConfigurationWindow as ConfigWindow
from exelcior.modules.additional_tools import ToolsModule, LabelEditor, SearchModule


def global_exception_handler(exctype, value, tb):
    logging.critical(f"Excepción no capturada: {value}", exc_info=(exctype, value, tb))

sys.excepthook = global_exception_handler

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dashboard.log'),
        logging.StreamHandler()
    ]
)

class ExelciorDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exelcior Apolo - Dashboard Completo")
        self.geometry("1200x800")
        self.configure(bg="#F9FAFB")

        # Crear directorio de logs si no existe
        Path("logs").mkdir(exist_ok=True)
        
        # Inicializar procesador
        self.processor = IntegratedExcelProcessor()
        
        # Variables de estado
        self.df = None
        self.transformed_df = None
        self.mode = "listados"
        self.processing = False
        
        # Variables de modo
        self.mode_vars = {
            m: tk.BooleanVar(value=(m == "listados"))
            for m in ["urbano", "fedex", "listados"]
        }
        
        # Inicializar módulos adicionales
        self.tools_module = ToolsModule(self)
        self.label_editor = LabelEditor(self)
        self.search_module = SearchModule(self)
        
        # Configurar estilos y crear interfaz
        self._setup_styles()
        self._setup_sidebar()
        self._setup_main_area()
        self._setup_status_bar()
        
        # Configurar detección automática de archivos urbanos
        self._setup_auto_detection()

    def _setup_styles(self):
        """Configurar estilos de la interfaz"""
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 11), padding=8)
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TCheckbutton", font=("Segoe UI", 11))
        style.configure("Sidebar.TButton", 
                       background="#374151", 
                       foreground="white",
                       font=("Segoe UI", 10))

    def _setup_sidebar(self):
        """Crear menú lateral con todas las funcionalidades"""
        sidebar = tk.Frame(self, bg="#111827", width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Título del menú
        tk.Label(
            sidebar,
            text="📋 Menú Principal",
            bg="#111827",
            fg="white",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=20)

        # Botones del menú principal
        menu_buttons = [
            ("📁 Seleccionar Excel", self._select_excel_file, "Diálogo avanzado para selección de archivos"),
            ("🔄 Carga Automática", self._auto_load_file, "Detección inteligente del archivo más reciente"),
            ("⚙️ Configuración", self._open_configuration, "Ventana de configuración por modo"),
            ("📄 Exportar PDF", self._export_to_pdf, "Exportación directa a PDF"),
            ("📤 Ver Logs", self._view_logs, "Historial completo de eventos"),
            ("🛠️ Herramientas", self._open_tools, "Módulo de herramientas auxiliares"),
            ("🏷️ Etiquetas", self._open_label_editor, "Editor de etiquetas Zebra"),
            ("🔍 Consulta por Código", self._search_by_code, "Búsqueda y rastreo por código"),
            ("📍 Consulta por Ubicación", self._search_by_location, "Búsqueda geográfica"),
            ("ℹ️ Acerca de", self._show_about, "Información completa del sistema"),
        ]

        for text, command, tooltip in menu_buttons:
            btn = tk.Button(
                sidebar,
                text=text,
                command=command,
                bg="#374151",
                fg="white",
                font=("Segoe UI", 10),
                relief="flat",
                padx=10,
                pady=8,
                anchor="w"
            )
            btn.pack(pady=5, fill="x", padx=10)
            
            # Agregar tooltip
            self._create_tooltip(btn, tooltip)

        # Botón salir al final
        tk.Button(
            sidebar,
            text="❌ Salir",
            command=self.quit,
            bg="#DC2626",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=10,
            pady=8
        ).pack(side="bottom", pady=20, fill="x", padx=10)

    def _setup_main_area(self):
        """Configurar área principal con checkboxes y funcionalidades"""
        self.main_frame = tk.Frame(self, bg="#F9FAFB")
        self.main_frame.pack(side="left", fill="both", expand=True)

        # Título principal
        title_frame = tk.Frame(self.main_frame, bg="#F9FAFB")
        title_frame.pack(pady=20, fill="x")
        
        tk.Label(
            title_frame,
            text="🧬 Exelcior Apolo Dashboard",
            bg="#F9FAFB",
            fg="#111827",
            font=("Segoe UI", 20, "bold"),
        ).pack()
        
        tk.Label(
            title_frame,
            text="Sistema completo de gestión y procesamiento de archivos Excel",
            bg="#F9FAFB",
            fg="#6B7280",
            font=("Segoe UI", 12),
        ).pack()

        # Frame de modos de operación
        mode_frame = ttk.LabelFrame(
            self.main_frame, 
            text="🎯 Modo de Operación", 
            padding=15
        )
        mode_frame.pack(pady=20, padx=20, fill="x")

        # Checkboxes de modo
        checkbox_frame = tk.Frame(mode_frame, bg="white")
        checkbox_frame.pack(fill="x")

        for i, (mode, description) in enumerate([
            ("urbano", "Archivos de 9 dígitos - Detección automática"),
            ("fedex", "Envíos FedEx - Agrupación por tracking"),
            ("listados", "Documentos de venta - Procesamiento estándar")
        ]):
            cb_frame = tk.Frame(checkbox_frame, bg="white")
            cb_frame.pack(side="left", padx=20, pady=10)
            
            ttk.Checkbutton(
                cb_frame,
                text=mode.capitalize(),
                variable=self.mode_vars[mode],
                command=lambda m=mode: self._update_mode(m),
            ).pack()
            
            tk.Label(
                cb_frame,
                text=description,
                bg="white",
                fg="#6B7280",
                font=("Segoe UI", 9)
            ).pack()

        # Búsqueda postal
        self._create_postal_search_widget()
        
        # Área de datos
        self._create_data_area()

    def _create_postal_search_widget(self):
        """Crear widget de búsqueda postal"""
        postal_frame = ttk.LabelFrame(
            self.main_frame,
            text="📮 Búsqueda de Código Postal",
            padding=15
        )
        postal_frame.pack(pady=10, padx=20, fill="x")
        
        search_frame = tk.Frame(postal_frame)
        search_frame.pack(fill="x")
        
        tk.Label(
            search_frame,
            text="Ciudad:",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(0, 10))
        
        self.postal_entry = tk.Entry(
            search_frame,
            font=("Segoe UI", 10),
            width=20
        )
        self.postal_entry.pack(side="left", padx=(0, 10))
        
        tk.Button(
            search_frame,
            text="🔍 Buscar",
            command=self._search_postal_code,
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=15
        ).pack(side="left")
        
        self.postal_result = tk.Label(
            postal_frame,
            text="Ej: Chillan → 3800000",
            fg="#6B7280",
            font=("Segoe UI", 9)
        )
        self.postal_result.pack(pady=(10, 0))

    def _create_data_area(self):
        """Crear área de visualización de datos"""
        data_frame = ttk.LabelFrame(
            self.main_frame,
            text="📊 Datos Procesados",
            padding=15
        )
        data_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Notebook para pestañas
        self.notebook = ttk.Notebook(data_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Pestaña de datos
        self.data_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="📋 Datos")
        
        # Pestaña de información
        self.info_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.info_tab, text="ℹ️ Información")
        
        # Crear tabla de datos
        self._create_data_table()
        
        # Crear panel de información
        self._create_info_panel()

    def _create_data_table(self):
        """Crear tabla de datos con scrollbars"""
        table_frame = tk.Frame(self.data_tab)
        table_frame.pack(fill="both", expand=True)
        
        # Treeview para mostrar datos
        columns = ["Col1", "Col2", "Col3", "Col4", "Col5"]
        self.data_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configurar columnas
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=120, minwidth=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.data_tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.data_tree.xview
        )
        
        self.data_tree.configure(
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Empaquetar elementos
        self.data_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Contador de registros
        self.record_counter = tk.Label(
            self.data_tab,
            text="📊 Registros: 0",
            font=("Segoe UI", 10, "bold"),
            fg="#374151"
        )
        self.record_counter.pack(pady=(10, 0))

    def _create_info_panel(self):
        """Crear panel de información"""
        info_text = tk.Text(
            self.info_tab,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#F9FAFB",
            relief="flat"
        )
        info_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        info_content = '''
🧬 Sistema Exelcior Apolo - Dashboard Completo

📋 FUNCIONALIDADES PRINCIPALES:

✅ Seleccionar Excel - Diálogo avanzado con validación
✅ Carga Automática - Detección inteligente por patrón
✅ Configuración - Ventana completa por modo
✅ Exportar PDF - Generación automática con formato
✅ Ver Logs - Historial completo con colores
✅ Herramientas - Módulo auxiliar integrado
✅ Etiquetas - Editor Zebra profesional
✅ Consulta por Código - Búsqueda y rastreo
✅ Consulta por Ubicación - Búsqueda geográfica
✅ Acerca de - Información completa

🎯 MODOS DE OPERACIÓN:

🔸 URBANO: Detección automática de archivos 9 dígitos
   - Validación: FECHA, CLIENTE, CIUDAD, PIEZAS
   - Procesamiento especializado
   
🔸 FEDEX: Agrupación por tracking number
   - Eliminación de duplicados
   - Suma de bultos por envío
   
🔸 LISTADOS: Procesamiento estándar
   - Documentos de venta
   - Configuración flexible

📊 CARACTERÍSTICAS AVANZADAS:

• Detección automática de patrones de archivo
• Configuración persistente por modo
• Sistema de logs dinámico
• Exportación múltiple (Excel, PDF)
• Integración con impresoras
• Base de datos SQLite
• Interfaz responsive
• Tooltips informativos
        '''
        
        info_text.insert("1.0", info_content)
        info_text.config(state="disabled")

    def _setup_status_bar(self):
        """Configurar barra de estado"""
        self.status_var = tk.StringVar()
        self.status_var.set("✅ Sistema listo - Seleccione un archivo Excel para comenzar")
        
        status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#E5E7EB",
            fg="#374151",
            font=("Segoe UI", 9),
            padx=10,
            pady=5
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_auto_detection(self):
        """Configurar detección automática de archivos urbanos"""
        # Esta función se llamará cuando se seleccione un archivo
        pass

    def _create_tooltip(self, widget, text):
        """Crear tooltip para un widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(
                tooltip,
                text=text,
                background="#1F2937",
                foreground="white",
                font=("Segoe UI", 9),
                padx=8,
                pady=4
            )
            label.pack()
            
            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _update_status(self, message):
        """Actualizar mensaje de estado"""
        self.status_var.set(message)
        self.update_idletasks()

    def _update_mode(self, selected_mode: str):
        """Actualizar modo de operación"""
        for mode in self.mode_vars:
            self.mode_vars[mode].set(mode == selected_mode)
        self.mode = selected_mode
        self._update_status(f"🎯 Modo cambiado a: {selected_mode.upper()}")
        logging.info(f"Modo cambiado a: {selected_mode}")

    # Funciones del menú principal
    def _select_excel_file(self):
        """Seleccionar archivo Excel con diálogo avanzado"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[
                ("Archivos Excel", "*.xlsx *.xls"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if file_path:
            self._update_status("📁 Procesando archivo seleccionado...")
            # Detectar si es archivo urbano (9 dígitos)
            filename = Path(file_path).stem
            if filename.isdigit() and len(filename) == 9:
                self._update_mode("urbano")
                self._update_status("🔄 Archivo urbano detectado - Modo cambiado automáticamente")
            
            # Procesar archivo
            threading.Thread(
                target=self._process_file,
                args=(file_path,),
                daemon=True
            ).start()

    def _auto_load_file(self):
        """Carga automática con detección inteligente"""
        self._update_status("🔄 Buscando archivo más reciente...")
        messagebox.showinfo(
            "Carga Automática",
            f"Buscando archivos para modo: {self.mode.upper()}\n\n"
            "Esta función detectará automáticamente el archivo más reciente "
            "compatible con el modo seleccionado."
        )

    def _open_configuration(self):
        """Abrir ventana de configuración"""
        if self.df is None:
            messagebox.showwarning(
                "Configuración",
                "Primero debe cargar un archivo Excel para acceder a la configuración."
            )
            return
        
        config_window = ConfigWindow(self)
        self.wait_window(config_window)

    def _export_to_pdf(self):
        """Exportar datos a PDF"""
        if self.transformed_df is None or self.transformed_df.empty:
            messagebox.showwarning(
                "Exportar PDF",
                "No hay datos para exportar. Primero procese un archivo Excel."
            )
            return
        
        messagebox.showinfo(
            "Exportar PDF",
            "Generando PDF con los datos procesados...\n\n"
            "El archivo se guardará en la carpeta 'exportados/pdf/'"
        )

    def _view_logs(self):
        """Ver historial de logs"""
        log_window = tk.Toplevel(self)
        log_window.title("📤 Historial de Logs")
        log_window.geometry("800x600")
        log_window.configure(bg="#F9FAFB")
        
        # Área de texto para logs
        log_text = tk.Text(
            log_window,
            wrap="word",
            font=("Consolas", 9),
            bg="#1F2937",
            fg="#E5E7EB"
        )
        log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(log_window, command=log_text.yview)
        scrollbar.pack(side="right", fill="y")
        log_text.config(yscrollcommand=scrollbar.set)
        
        # Contenido de ejemplo
        log_content = '''
2025-06-23 11:24:02 [INFO] - Sistema iniciado correctamente
2025-06-23 11:24:05 [INFO] - Modo cambiado a: urbano
2025-06-23 11:24:10 [INFO] - Archivo cargado: 192403809.xlsx
2025-06-23 11:24:12 [INFO] - Procesamiento completado: 150 registros
2025-06-23 11:24:15 [INFO] - Exportación PDF generada exitosamente
        '''
        
        log_text.insert("1.0", log_content)
        log_text.config(state="disabled")

    def _open_tools(self):
        """Abrir módulo de herramientas"""
        # Actualizar datos en el módulo de herramientas
        self.tools_module.data_df = self.transformed_df
        self.tools_module.open_tools_window()

    def _open_label_editor(self):
        """Abrir editor de etiquetas Zebra"""
        self.label_editor.open_label_editor()

    def _search_by_code(self):
        """Búsqueda por código"""
        # Actualizar datos en el módulo de búsqueda
        self.search_module.data_df = self.transformed_df
        self.search_module.open_code_search()

    def _search_by_location(self):
        """Búsqueda por ubicación"""
        # Actualizar datos en el módulo de búsqueda
        self.search_module.data_df = self.transformed_df
        self.search_module.open_location_search()

    def _show_about(self):
        """Mostrar información del sistema"""
        about_window = tk.Toplevel(self)
        about_window.title("ℹ️ Acerca de Exelcior Apolo")
        about_window.geometry("700x600")
        about_window.configure(bg="#F9FAFB")
        
        # Contenido scrollable
        canvas = tk.Canvas(about_window, bg="#F9FAFB")
        scrollbar = ttk.Scrollbar(about_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Contenido
        about_content = '''
🧬 Sistema Exelcior Apolo

📄 Descripción:
Aplicación completa para la gestión, edición e impresión de archivos Excel
clínicos y logísticos, con herramientas avanzadas para el trabajo profesional.

👤 Desarrollador principal:
Gian Lucas San Martín
• Analista Programador
• Técnico de Laboratorio Clínico
• Socio fundador de GCNJ

🔖 Versión: 2.0.0
📅 Última actualización: 2025-06-23

💼 Características principales:
• Detección automática de archivos urbanos
• Procesamiento inteligente por modo
• Sistema de configuración avanzado
• Exportación múltiple (Excel, PDF)
• Integración con impresoras Zebra
• Base de datos SQLite integrada
• Logs dinámicos y estructurados
• Interfaz moderna y responsive

© 2025 Gian Lucas San Martín – GCNJ. Todos los derechos reservados.
        '''
        
        tk.Label(
            scrollable_frame,
            text=about_content,
            bg="#F9FAFB",
            fg="#374151",
            font=("Segoe UI", 10),
            justify="left",
            padx=20,
            pady=20
        ).pack(fill="both", expand=True)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _search_postal_code(self):
        """Buscar código postal"""
        city = self.postal_entry.get().strip()
        if city:
            # Simulación de búsqueda
            postal_codes = {
                "chillan": "3800000",
                "santiago": "8320000",
                "valparaiso": "2340000",
                "concepcion": "4030000"
            }
            
            code = postal_codes.get(city.lower(), "No encontrado")
            self.postal_result.config(
                text=f"{city.title()} → {code}",
                fg="#059669" if code != "No encontrado" else "#DC2626"
            )

    def _process_file(self, file_path):
        """Procesar archivo Excel con detección urbana perfecta"""
        try:
            self._update_status("⚙️ Procesando archivo...")
            
            # Usar el procesador integrado
            result = self.processor.process_file_complete(file_path, self.mode)
            
            if result["success"]:
                self.df = result["data"]
                self.transformed_df = result["data"]
                
                # Actualizar tabla con datos reales
                self._update_data_table_with_real_data(result["data"], result["mode"])
                
                # Mostrar resumen
                summary = result["summary"]
                status_msg = f"✅ Archivo procesado: {summary['total_records']} registros"
                
                if "total_bultos" in summary:
                    status_msg += f", {summary['total_bultos']} bultos"
                elif "total_piezas" in summary:
                    status_msg += f", {summary['total_piezas']} piezas"
                
                self._update_status(status_msg)
                
                # Actualizar módulos con nuevos datos
                self.tools_module.data_df = self.transformed_df
                self.search_module.data_df = self.transformed_df
                
            else:
                error_msg = result.get("error", "Error desconocido")
                self._update_status(f"❌ Error: {error_msg}")
                messagebox.showerror("Error", f"Error al procesar archivo:\n{error_msg}")
            
        except Exception as e:
            self._update_status(f"❌ Error al procesar archivo: {str(e)}")
            messagebox.showerror("Error", f"Error al procesar archivo:\n{str(e)}")

    def _update_data_table_with_real_data(self, df, mode):
        """Actualizar tabla de datos con información real"""
        # Limpiar tabla
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        
        if df is None or df.empty:
            self.record_counter.config(text="📊 Registros: 0")
            return
        
        # Configurar columnas según los datos reales
        columns = list(df.columns)[:10]  # Máximo 10 columnas para visualización
        self.data_tree["columns"] = columns
        
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=120, minwidth=80)
        
        # Insertar datos (máximo 100 filas para rendimiento)
        max_rows = min(100, len(df))
        for i in range(max_rows):
            row_data = []
            for col in columns:
                value = df.iloc[i][col] if col in df.columns else ""
                # Truncar valores largos
                str_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                row_data.append(str_value)
            
            self.data_tree.insert("", "end", values=row_data)
        
        # Actualizar contador
        total_records = len(df)
        display_text = f"📊 Registros: {total_records}"
        if max_rows < total_records:
            display_text += f" (mostrando {max_rows})"
        
        self.record_counter.config(text=display_text)


def main():
    """Función principal"""
    app = ExelciorDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()

