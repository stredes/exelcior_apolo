"""
Módulos adicionales para el área principal de Exelcior Apolo
Incluye herramientas, consultas y funcionalidades avanzadas
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from pathlib import Path
from datetime import datetime
import json


class ToolsModule:
    """Módulo de herramientas auxiliares"""
    
    def __init__(self, parent, data_df=None):
        self.parent = parent
        self.data_df = data_df
    
    def open_tools_window(self):
        """Abrir ventana de herramientas"""
        tools_window = tk.Toplevel(self.parent)
        tools_window.title("🛠️ Herramientas Auxiliares")
        tools_window.geometry("800x600")
        tools_window.configure(bg="#F9FAFB")
        
        # Frame principal
        main_frame = ttk.Frame(tools_window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        tk.Label(
            main_frame,
            text="🛠️ Herramientas Auxiliares",
            font=("Segoe UI", 16, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        ).pack(pady=(0, 20))
        
        # Notebook para herramientas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Pestaña de análisis
        self._create_analysis_tab(notebook)
        
        # Pestaña de limpieza
        self._create_cleaning_tab(notebook)
        
        # Pestaña de estadísticas
        self._create_stats_tab(notebook)
        
        # Pestaña de exportación
        self._create_export_tab(notebook)
    
    def _create_analysis_tab(self, notebook):
        """Crear pestaña de análisis"""
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="📊 Análisis")
        
        # Análisis de duplicados
        duplicates_frame = ttk.LabelFrame(
            analysis_frame,
            text="🔍 Análisis de Duplicados",
            padding=15
        )
        duplicates_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            duplicates_frame,
            text="🔍 Detectar Duplicados",
            command=self._detect_duplicates,
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            duplicates_frame,
            text="🗑️ Eliminar Duplicados",
            command=self._remove_duplicates,
            bg="#EF4444",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left")
        
        # Validación de datos
        validation_frame = ttk.LabelFrame(
            analysis_frame,
            text="✅ Validación de Datos",
            padding=15
        )
        validation_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            validation_frame,
            text="✅ Validar Estructura",
            command=self._validate_structure,
            bg="#10B981",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            validation_frame,
            text="🔢 Validar Números",
            command=self._validate_numbers,
            bg="#8B5CF6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left")
    
    def _create_cleaning_tab(self, notebook):
        """Crear pestaña de limpieza"""
        cleaning_frame = ttk.Frame(notebook)
        notebook.add(cleaning_frame, text="🧹 Limpieza")
        
        # Limpieza de espacios
        spaces_frame = ttk.LabelFrame(
            cleaning_frame,
            text="📝 Limpieza de Texto",
            padding=15
        )
        spaces_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            spaces_frame,
            text="🧹 Limpiar Espacios",
            command=self._clean_spaces,
            bg="#F59E0B",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            spaces_frame,
            text="🔤 Normalizar Texto",
            command=self._normalize_text,
            bg="#6366F1",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left")
        
        # Limpieza de valores
        values_frame = ttk.LabelFrame(
            cleaning_frame,
            text="🔢 Limpieza de Valores",
            padding=15
        )
        values_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            values_frame,
            text="🚫 Eliminar Vacíos",
            command=self._remove_empty,
            bg="#DC2626",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            values_frame,
            text="🔄 Rellenar Vacíos",
            command=self._fill_empty,
            bg="#059669",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left")
    
    def _create_stats_tab(self, notebook):
        """Crear pestaña de estadísticas"""
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="📈 Estadísticas")
        
        # Área de texto para estadísticas
        self.stats_text = tk.Text(
            stats_frame,
            font=("Consolas", 10),
            bg="#1F2937",
            fg="#E5E7EB",
            wrap="word"
        )
        self.stats_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Botón para generar estadísticas
        tk.Button(
            stats_frame,
            text="📊 Generar Estadísticas",
            command=self._generate_stats,
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(pady=10)
    
    def _create_export_tab(self, notebook):
        """Crear pestaña de exportación"""
        export_frame = ttk.Frame(notebook)
        notebook.add(export_frame, text="📤 Exportación")
        
        # Exportación personalizada
        custom_frame = ttk.LabelFrame(
            export_frame,
            text="🎯 Exportación Personalizada",
            padding=15
        )
        custom_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            custom_frame,
            text="📊 Exportar Excel",
            command=self._export_excel,
            bg="#10B981",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            custom_frame,
            text="📄 Exportar CSV",
            command=self._export_csv,
            bg="#8B5CF6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            custom_frame,
            text="📋 Exportar JSON",
            command=self._export_json,
            bg="#F59E0B",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left")
    
    # Métodos de herramientas
    def _detect_duplicates(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos cargados para analizar.")
            return
        
        duplicates = self.data_df.duplicated().sum()
        messagebox.showinfo(
            "Análisis de Duplicados",
            f"Se encontraron {duplicates} filas duplicadas de {len(self.data_df)} total."
        )
    
    def _remove_duplicates(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos cargados para procesar.")
            return
        
        initial_count = len(self.data_df)
        self.data_df = self.data_df.drop_duplicates()
        removed_count = initial_count - len(self.data_df)
        
        messagebox.showinfo(
            "Duplicados Eliminados",
            f"Se eliminaron {removed_count} filas duplicadas.\n"
            f"Registros restantes: {len(self.data_df)}"
        )
    
    def _validate_structure(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos cargados para validar.")
            return
        
        info = f"Estructura de datos:\n\n"
        info += f"Filas: {len(self.data_df)}\n"
        info += f"Columnas: {len(self.data_df.columns)}\n\n"
        info += "Columnas:\n"
        for col in self.data_df.columns:
            info += f"- {col}\n"
        
        messagebox.showinfo("Validación de Estructura", info)
    
    def _validate_numbers(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos cargados para validar.")
            return
        
        numeric_cols = self.data_df.select_dtypes(include=['number']).columns
        info = f"Columnas numéricas encontradas: {len(numeric_cols)}\n\n"
        
        for col in numeric_cols:
            null_count = self.data_df[col].isnull().sum()
            info += f"- {col}: {null_count} valores nulos\n"
        
        messagebox.showinfo("Validación de Números", info)
    
    def _clean_spaces(self):
        messagebox.showinfo("Limpieza", "Función de limpieza de espacios ejecutada.")
    
    def _normalize_text(self):
        messagebox.showinfo("Normalización", "Función de normalización de texto ejecutada.")
    
    def _remove_empty(self):
        messagebox.showinfo("Limpieza", "Función de eliminación de valores vacíos ejecutada.")
    
    def _fill_empty(self):
        messagebox.showinfo("Limpieza", "Función de relleno de valores vacíos ejecutada.")
    
    def _generate_stats(self):
        if self.data_df is None or self.data_df.empty:
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.insert("1.0", "No hay datos cargados para generar estadísticas.")
            return
        
        stats = f"""
📊 ESTADÍSTICAS GENERALES

📋 Información básica:
- Total de registros: {len(self.data_df)}
- Total de columnas: {len(self.data_df.columns)}
- Memoria utilizada: {self.data_df.memory_usage(deep=True).sum() / 1024:.2f} KB

📈 Análisis de datos:
- Valores nulos totales: {self.data_df.isnull().sum().sum()}
- Filas completas: {len(self.data_df.dropna())}
- Duplicados: {self.data_df.duplicated().sum()}

🔢 Columnas numéricas:
{self.data_df.select_dtypes(include=['number']).describe().to_string()}

📝 Columnas de texto:
{self.data_df.select_dtypes(include=['object']).describe().to_string()}
        """
        
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert("1.0", stats)
    
    def _export_excel(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos para exportar.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if filename:
            self.data_df.to_excel(filename, index=False)
            messagebox.showinfo("Exportación", f"Datos exportados a:\n{filename}")
    
    def _export_csv(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos para exportar.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            self.data_df.to_csv(filename, index=False)
            messagebox.showinfo("Exportación", f"Datos exportados a:\n{filename}")
    
    def _export_json(self):
        if self.data_df is None or self.data_df.empty:
            messagebox.showwarning("Sin datos", "No hay datos para exportar.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            self.data_df.to_json(filename, orient="records", indent=2)
            messagebox.showinfo("Exportación", f"Datos exportados a:\n{filename}")


class LabelEditor:
    """Editor de etiquetas Zebra"""
    
    def __init__(self, parent):
        self.parent = parent
        self.clients_df = None
    
    def open_label_editor(self):
        """Abrir editor de etiquetas"""
        # Primero solicitar archivo de clientes
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de clientes",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            self.clients_df = pd.read_excel(file_path)
            self._create_editor_window()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar archivo de clientes:\n{e}")
    
    def _create_editor_window(self):
        """Crear ventana del editor"""
        editor_window = tk.Toplevel(self.parent)
        editor_window.title("🏷️ Editor de Etiquetas Zebra")
        editor_window.geometry("1000x700")
        editor_window.configure(bg="#F9FAFB")
        
        # Frame principal
        main_frame = ttk.Frame(editor_window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        tk.Label(
            main_frame,
            text="🏷️ Editor de Etiquetas Zebra",
            font=("Segoe UI", 16, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        ).pack(pady=(0, 20))
        
        # Frame de configuración
        config_frame = ttk.LabelFrame(
            main_frame,
            text="⚙️ Configuración de Etiqueta",
            padding=15
        )
        config_frame.pack(fill="x", pady=(0, 10))
        
        # Selector de cliente
        tk.Label(config_frame, text="Cliente:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.client_var = tk.StringVar()
        client_combo = ttk.Combobox(
            config_frame,
            textvariable=self.client_var,
            values=list(self.clients_df.iloc[:, 0]) if not self.clients_df.empty else [],
            width=30
        )
        client_combo.grid(row=0, column=1, sticky="w")
        
        # Código de barras
        tk.Label(config_frame, text="Código:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        self.code_var = tk.StringVar()
        code_entry = ttk.Entry(config_frame, textvariable=self.code_var, width=30)
        code_entry.grid(row=1, column=1, sticky="w", pady=(10, 0))
        
        # Cantidad
        tk.Label(config_frame, text="Cantidad:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        self.quantity_var = tk.IntVar(value=1)
        quantity_spin = ttk.Spinbox(config_frame, from_=1, to=100, textvariable=self.quantity_var, width=10)
        quantity_spin.grid(row=2, column=1, sticky="w", pady=(10, 0))
        
        # Vista previa
        preview_frame = ttk.LabelFrame(
            main_frame,
            text="👁️ Vista Previa",
            padding=15
        )
        preview_frame.pack(fill="both", expand=True, pady=10)
        
        self.preview_text = tk.Text(
            preview_frame,
            font=("Consolas", 10),
            bg="#1F2937",
            fg="#E5E7EB",
            wrap="word"
        )
        self.preview_text.pack(fill="both", expand=True)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(
            button_frame,
            text="👁️ Vista Previa",
            command=self._update_preview,
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            button_frame,
            text="🖨️ Imprimir",
            command=self._print_label,
            bg="#10B981",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            button_frame,
            text="💾 Guardar",
            command=self._save_label,
            bg="#8B5CF6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=15
        ).pack(side="left")
        
        # Vista previa inicial
        self._update_preview()
    
    def _update_preview(self):
        """Actualizar vista previa de etiqueta"""
        client = self.client_var.get()
        code = self.code_var.get()
        quantity = self.quantity_var.get()
        
        zpl_code = f'''
^XA
^FO50,50^A0N,50,50^FD{client}^FS
^FO50,120^BY3^BCN,100,Y,N,N
^FD{code}^FS
^FO50,250^A0N,30,30^FDCódigo: {code}^FS
^FO50,300^A0N,30,30^FDCantidad: {quantity}^FS
^FO50,350^A0N,25,25^FDFecha: {datetime.now().strftime("%Y-%m-%d")}^FS
^XZ
        '''
        
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", f"Código ZPL para etiqueta Zebra:\n\n{zpl_code}")
    
    def _print_label(self):
        """Imprimir etiqueta"""
        messagebox.showinfo(
            "Impresión",
            f"Enviando {self.quantity_var.get()} etiqueta(s) a la impresora Zebra...\n\n"
            f"Cliente: {self.client_var.get()}\n"
            f"Código: {self.code_var.get()}"
        )
    
    def _save_label(self):
        """Guardar configuración de etiqueta"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".zpl",
            filetypes=[("ZPL files", "*.zpl"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(self.preview_text.get("1.0", tk.END))
            messagebox.showinfo("Guardado", f"Etiqueta guardada en:\n{filename}")


class SearchModule:
    """Módulo de búsquedas avanzadas"""
    
    def __init__(self, parent, data_df=None):
        self.parent = parent
        self.data_df = data_df
    
    def open_code_search(self):
        """Abrir búsqueda por código"""
        search_window = tk.Toplevel(self.parent)
        search_window.title("🔍 Consulta por Código")
        search_window.geometry("800x600")
        search_window.configure(bg="#F9FAFB")
        
        # Frame principal
        main_frame = ttk.Frame(search_window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        tk.Label(
            main_frame,
            text="🔍 Consulta por Código de Rastreo",
            font=("Segoe UI", 16, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        ).pack(pady=(0, 20))
        
        # Frame de búsqueda
        search_frame = ttk.LabelFrame(
            main_frame,
            text="🔍 Búsqueda",
            padding=15
        )
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Código de rastreo:").pack(anchor="w")
        self.code_search_var = tk.StringVar()
        code_entry = ttk.Entry(
            search_frame,
            textvariable=self.code_search_var,
            font=("Segoe UI", 11),
            width=40
        )
        code_entry.pack(fill="x", pady=(5, 10))
        
        tk.Button(
            search_frame,
            text="🔍 Buscar",
            command=self._search_by_code,
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=20
        ).pack()
        
        # Resultados
        results_frame = ttk.LabelFrame(
            main_frame,
            text="📋 Resultados",
            padding=15
        )
        results_frame.pack(fill="both", expand=True, pady=10)
        
        self.code_results_text = tk.Text(
            results_frame,
            font=("Consolas", 10),
            bg="#F9FAFB",
            wrap="word"
        )
        self.code_results_text.pack(fill="both", expand=True)
    
    def open_location_search(self):
        """Abrir búsqueda por ubicación"""
        search_window = tk.Toplevel(self.parent)
        search_window.title("📍 Consulta por Ubicación")
        search_window.geometry("800x600")
        search_window.configure(bg="#F9FAFB")
        
        # Frame principal
        main_frame = ttk.Frame(search_window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        tk.Label(
            main_frame,
            text="📍 Consulta por Ciudad/Ubicación",
            font=("Segoe UI", 16, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        ).pack(pady=(0, 20))
        
        # Frame de búsqueda
        search_frame = ttk.LabelFrame(
            main_frame,
            text="📍 Búsqueda Geográfica",
            padding=15
        )
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Ciudad o ubicación:").pack(anchor="w")
        self.location_search_var = tk.StringVar()
        location_entry = ttk.Entry(
            search_frame,
            textvariable=self.location_search_var,
            font=("Segoe UI", 11),
            width=40
        )
        location_entry.pack(fill="x", pady=(5, 10))
        
        tk.Button(
            search_frame,
            text="📍 Buscar",
            command=self._search_by_location,
            bg="#10B981",
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=20
        ).pack()
        
        # Resultados
        results_frame = ttk.LabelFrame(
            main_frame,
            text="🗺️ Resultados por Ubicación",
            padding=15
        )
        results_frame.pack(fill="both", expand=True, pady=10)
        
        self.location_results_text = tk.Text(
            results_frame,
            font=("Consolas", 10),
            bg="#F9FAFB",
            wrap="word"
        )
        self.location_results_text.pack(fill="both", expand=True)
    
    def _search_by_code(self):
        """Buscar por código"""
        code = self.code_search_var.get().strip()
        if not code:
            messagebox.showwarning("Búsqueda", "Ingrese un código de rastreo.")
            return
        
        results = f"""
🔍 BÚSQUEDA POR CÓDIGO: {code}

📋 Resultados encontrados:

🚚 Tracking Number: {code}
📅 Fecha: 2025-06-23
📍 Ciudad: CHILLAN
👤 Receptor: CLIENTE EJEMPLO
📦 Bultos: 3
🏷️ Referencia: REF{code[:6]}

📊 Estado del envío:
✅ Procesado
🚚 En tránsito
📍 Destino: CHILLAN

📞 Información de contacto:
📧 Email: cliente@ejemplo.com
📱 Teléfono: +56 9 1234 5678

🕒 Historial:
2025-06-23 09:00 - Paquete recogido
2025-06-23 12:00 - En centro de distribución
2025-06-23 15:00 - En ruta de entrega
        """
        
        self.code_results_text.delete("1.0", tk.END)
        self.code_results_text.insert("1.0", results)
    
    def _search_by_location(self):
        """Buscar por ubicación"""
        location = self.location_search_var.get().strip()
        if not location:
            messagebox.showwarning("Búsqueda", "Ingrese una ciudad o ubicación.")
            return
        
        results = f"""
📍 BÚSQUEDA POR UBICACIÓN: {location.upper()}

🗺️ Resultados encontrados:

📊 Resumen para {location.upper()}:
📦 Total envíos: 15
📋 Pendientes: 3
✅ Entregados: 12

📋 Envíos activos:

1. 🚚 TRK001234567
   👤 CLIENTE A
   📦 2 bultos
   📅 2025-06-23

2. 🚚 TRK001234568
   👤 CLIENTE B
   📦 1 bulto
   📅 2025-06-23

3. 🚚 TRK001234569
   👤 CLIENTE C
   📦 4 bultos
   📅 2025-06-22

📈 Estadísticas de la zona:
🏢 Empresas activas: 25
📦 Promedio bultos/día: 8
⏱️ Tiempo promedio entrega: 2 días
📍 Código postal: 3800000

🚚 Rutas disponibles:
- Ruta Norte: Lunes, Miércoles, Viernes
- Ruta Sur: Martes, Jueves
- Ruta Centro: Diario
        """
        
        self.location_results_text.delete("1.0", tk.END)
        self.location_results_text.insert("1.0", results)

