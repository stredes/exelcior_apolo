"""
Ventana de configuración avanzada para Exelcior Apolo
Permite configurar parámetros específicos por modo de operación
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
from typing import Dict, List, Any


class ConfigurationWindow(tk.Toplevel):
    """Ventana de configuración avanzada"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("⚙️ Configuración Avanzada - Exelcior Apolo")
        self.geometry("900x700")
        self.configure(bg="#F9FAFB")
        
        # Variables de configuración
        self.config_data = self._load_config()
        self.current_mode = "listados"
        
        # Crear interfaz
        self._create_widgets()
        self._load_current_config()
        
        # Centrar ventana
        self._center_window()
        
        # Hacer modal
        self.transient(parent)
        self.grab_set()
    
    def _load_config(self) -> Dict[str, Any]:
        """Cargar configuración desde archivo"""
        config_file = Path("config/user_config.json")
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Configuración por defecto
        return {
            "fedex": {
                "eliminar": [
                    "errors", "senderAccountNumber", "poNumber", "senderLine1",
                    "senderPostcode", "totalShipmentWeight", "weightUnits",
                    "recipientPostcode", "creationDate", "recipientPhoneExtension"
                ],
                "sumar": ["numberOfPackages"],
                "mantener_formato": ["masterTrackingNumber"],
                "start_row": 0,
                "vista_previa_fuente": 10,
            },
            "urbano": {
                "eliminar": [
                    "AGENCIA", "SHIPPER", "FECHA CHK", "DIAS", 
                    "ESTADO", "SERVICIO", "PESO"
                ],
                "sumar": ["PIEZAS"],
                "mantener_formato": [],
                "start_row": 2,
                "nombre_archivo_digitos": [9, 10],
                "vista_previa_fuente": 10,
            },
            "listados": {
                "eliminar": [
                    "Moneda", "Fecha doc.", "RUT", "Vendedor", 
                    "Glosa", "Total", "Tipo cambio"
                ],
                "sumar": [],
                "mantener_formato": [],
                "start_row": 0,
                "vista_previa_fuente": 10,
            },
        }
    
    def _save_config(self):
        """Guardar configuración a archivo"""
        config_file = Path("config/user_config.json")
        config_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración:\n{e}")
    
    def _center_window(self):
        """Centrar ventana en la pantalla"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="⚙️ Configuración Avanzada",
            font=("Segoe UI", 16, "bold"),
            bg="#F9FAFB",
            fg="#111827"
        )
        title_label.pack(pady=(0, 20))
        
        # Selector de modo
        self._create_mode_selector(main_frame)
        
        # Notebook para pestañas de configuración
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=10)
        
        # Pestañas
        self._create_columns_tab()
        self._create_processing_tab()
        self._create_display_tab()
        
        # Botones
        self._create_buttons(main_frame)
    
    def _create_mode_selector(self, parent):
        """Crear selector de modo"""
        mode_frame = ttk.LabelFrame(parent, text="🎯 Modo de Configuración", padding=10)
        mode_frame.pack(fill="x", pady=(0, 10))
        
        self.mode_var = tk.StringVar(value=self.current_mode)
        
        modes = [
            ("urbano", "🏢 Urbano - Archivos de 9 dígitos"),
            ("fedex", "📦 FedEx - Envíos internacionales"),
            ("listados", "📋 Listados - Documentos de venta")
        ]
        
        for mode, description in modes:
            rb = ttk.Radiobutton(
                mode_frame,
                text=description,
                variable=self.mode_var,
                value=mode,
                command=self._on_mode_change
            )
            rb.pack(anchor="w", pady=2)
    
    def _create_columns_tab(self):
        """Crear pestaña de configuración de columnas"""
        columns_frame = ttk.Frame(self.notebook)
        self.notebook.add(columns_frame, text="📊 Columnas")
        
        # Frame principal con scroll
        canvas = tk.Canvas(columns_frame, bg="#F9FAFB")
        scrollbar = ttk.Scrollbar(columns_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Columnas a eliminar
        eliminar_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="🗑️ Columnas a Eliminar", 
            padding=10
        )
        eliminar_frame.pack(fill="x", padx=10, pady=5)
        
        self.eliminar_text = tk.Text(
            eliminar_frame,
            height=8,
            font=("Consolas", 9),
            wrap="word"
        )
        self.eliminar_text.pack(fill="x")
        
        # Columnas para sumar
        sumar_frame = ttk.LabelFrame(
            scrollable_frame,
            text="➕ Columnas para Sumar",
            padding=10
        )
        sumar_frame.pack(fill="x", padx=10, pady=5)
        
        self.sumar_text = tk.Text(
            sumar_frame,
            height=4,
            font=("Consolas", 9),
            wrap="word"
        )
        self.sumar_text.pack(fill="x")
        
        # Columnas a mantener formato
        formato_frame = ttk.LabelFrame(
            scrollable_frame,
            text="🔒 Mantener Formato Original",
            padding=10
        )
        formato_frame.pack(fill="x", padx=10, pady=5)
        
        self.formato_text = tk.Text(
            formato_frame,
            height=4,
            font=("Consolas", 9),
            wrap="word"
        )
        self.formato_text.pack(fill="x")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_processing_tab(self):
        """Crear pestaña de configuración de procesamiento"""
        processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(processing_frame, text="⚙️ Procesamiento")
        
        # Fila de inicio
        start_row_frame = ttk.LabelFrame(
            processing_frame,
            text="📍 Fila de Inicio de Datos",
            padding=15
        )
        start_row_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(
            start_row_frame,
            text="Especifica desde qué fila comenzar a leer los datos (0 = primera fila):",
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        
        self.start_row_var = tk.IntVar()
        start_row_spin = ttk.Spinbox(
            start_row_frame,
            from_=0,
            to=50,
            textvariable=self.start_row_var,
            width=10,
            font=("Segoe UI", 11)
        )
        start_row_spin.pack(anchor="w", pady=(5, 0))
        
        # Configuración específica para Urbano
        self.urbano_frame = ttk.LabelFrame(
            processing_frame,
            text="🏢 Configuración Urbano",
            padding=15
        )
        self.urbano_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(
            self.urbano_frame,
            text="Dígitos válidos para nombres de archivo (separados por coma):",
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        
        self.digitos_var = tk.StringVar()
        digitos_entry = ttk.Entry(
            self.urbano_frame,
            textvariable=self.digitos_var,
            font=("Segoe UI", 11),
            width=20
        )
        digitos_entry.pack(anchor="w", pady=(5, 0))
        
        tk.Label(
            self.urbano_frame,
            text="Ejemplo: 9,10 (archivos de 9 o 10 dígitos)",
            font=("Segoe UI", 9),
            fg="#6B7280"
        ).pack(anchor="w", pady=(2, 0))
    
    def _create_display_tab(self):
        """Crear pestaña de configuración de visualización"""
        display_frame = ttk.Frame(self.notebook)
        self.notebook.add(display_frame, text="🎨 Visualización")
        
        # Tamaño de fuente
        font_frame = ttk.LabelFrame(
            display_frame,
            text="🔤 Tamaño de Fuente",
            padding=15
        )
        font_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(
            font_frame,
            text="Tamaño de fuente para vista previa de datos:",
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        
        self.font_size_var = tk.IntVar()
        font_spin = ttk.Spinbox(
            font_frame,
            from_=8,
            to=24,
            textvariable=self.font_size_var,
            width=10,
            font=("Segoe UI", 11)
        )
        font_spin.pack(anchor="w", pady=(5, 0))
        
        # Vista previa
        preview_frame = ttk.LabelFrame(
            display_frame,
            text="👁️ Vista Previa",
            padding=15
        )
        preview_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.preview_text = tk.Text(
            preview_frame,
            height=10,
            font=("Consolas", 10),
            bg="#1F2937",
            fg="#E5E7EB",
            wrap="word"
        )
        self.preview_text.pack(fill="both", expand=True)
        
        # Contenido de vista previa
        preview_content = '''
🧬 Configuración Actual:

📊 Modo: {mode}
📍 Fila inicio: {start_row}
🗑️ Columnas a eliminar: {eliminar_count}
➕ Columnas a sumar: {sumar_count}
🔒 Mantener formato: {formato_count}
🔤 Tamaño fuente: {font_size}

✅ La configuración se aplicará automáticamente
   al procesar archivos en este modo.
        '''
        
        self.preview_text.insert("1.0", preview_content)
        self.preview_text.config(state="disabled")
    
    def _create_buttons(self, parent):
        """Crear botones de acción"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(20, 0))
        
        # Botones a la izquierda
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side="left")
        
        ttk.Button(
            left_buttons,
            text="🔄 Restablecer",
            command=self._reset_to_default
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            left_buttons,
            text="📋 Copiar Config",
            command=self._copy_config
        ).pack(side="left", padx=(0, 10))
        
        # Botones a la derecha
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side="right")
        
        ttk.Button(
            right_buttons,
            text="❌ Cancelar",
            command=self.destroy
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            right_buttons,
            text="💾 Guardar",
            command=self._save_and_close
        ).pack(side="left")
    
    def _on_mode_change(self):
        """Manejar cambio de modo"""
        self.current_mode = self.mode_var.get()
        self._load_current_config()
        self._update_preview()
        
        # Mostrar/ocultar configuración específica de Urbano
        if self.current_mode == "urbano":
            self.urbano_frame.pack(fill="x", padx=20, pady=10)
        else:
            self.urbano_frame.pack_forget()
    
    def _load_current_config(self):
        """Cargar configuración del modo actual"""
        config = self.config_data.get(self.current_mode, {})
        
        # Cargar columnas a eliminar
        eliminar = config.get("eliminar", [])
        self.eliminar_text.delete("1.0", tk.END)
        self.eliminar_text.insert("1.0", "\n".join(eliminar))
        
        # Cargar columnas a sumar
        sumar = config.get("sumar", [])
        self.sumar_text.delete("1.0", tk.END)
        self.sumar_text.insert("1.0", "\n".join(sumar))
        
        # Cargar columnas de formato
        formato = config.get("mantener_formato", [])
        self.formato_text.delete("1.0", tk.END)
        self.formato_text.insert("1.0", "\n".join(formato))
        
        # Cargar otros valores
        self.start_row_var.set(config.get("start_row", 0))
        self.font_size_var.set(config.get("vista_previa_fuente", 10))
        
        # Configuración específica de Urbano
        if self.current_mode == "urbano":
            digitos = config.get("nombre_archivo_digitos", [9, 10])
            self.digitos_var.set(",".join(map(str, digitos)))
    
    def _update_preview(self):
        """Actualizar vista previa"""
        config = self.config_data.get(self.current_mode, {})
        
        eliminar_count = len(config.get("eliminar", []))
        sumar_count = len(config.get("sumar", []))
        formato_count = len(config.get("mantener_formato", []))
        
        preview_content = f'''
🧬 Configuración Actual:

📊 Modo: {self.current_mode.upper()}
📍 Fila inicio: {self.start_row_var.get()}
🗑️ Columnas a eliminar: {eliminar_count}
➕ Columnas a sumar: {sumar_count}
🔒 Mantener formato: {formato_count}
🔤 Tamaño fuente: {self.font_size_var.get()}

✅ La configuración se aplicará automáticamente
   al procesar archivos en este modo.
        '''
        
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview_content)
        self.preview_text.config(state="disabled")
    
    def _reset_to_default(self):
        """Restablecer configuración por defecto"""
        if messagebox.askyesno(
            "Restablecer",
            f"¿Restablecer la configuración por defecto para el modo {self.current_mode.upper()}?"
        ):
            # Recargar configuración por defecto
            default_config = self._load_config()
            self.config_data[self.current_mode] = default_config[self.current_mode]
            self._load_current_config()
            self._update_preview()
    
    def _copy_config(self):
        """Copiar configuración al portapapeles"""
        config = self.config_data.get(self.current_mode, {})
        config_text = json.dumps(config, indent=2, ensure_ascii=False)
        
        self.clipboard_clear()
        self.clipboard_append(config_text)
        
        messagebox.showinfo(
            "Configuración Copiada",
            "La configuración ha sido copiada al portapapeles."
        )
    
    def _save_and_close(self):
        """Guardar configuración y cerrar ventana"""
        try:
            # Obtener valores de los campos
            eliminar = [
                line.strip() for line in self.eliminar_text.get("1.0", tk.END).split("\n")
                if line.strip()
            ]
            
            sumar = [
                line.strip() for line in self.sumar_text.get("1.0", tk.END).split("\n")
                if line.strip()
            ]
            
            formato = [
                line.strip() for line in self.formato_text.get("1.0", tk.END).split("\n")
                if line.strip()
            ]
            
            # Actualizar configuración
            self.config_data[self.current_mode] = {
                "eliminar": eliminar,
                "sumar": sumar,
                "mantener_formato": formato,
                "start_row": self.start_row_var.get(),
                "vista_previa_fuente": self.font_size_var.get(),
            }
            
            # Configuración específica de Urbano
            if self.current_mode == "urbano":
                try:
                    digitos_str = self.digitos_var.get().strip()
                    if digitos_str:
                        digitos = [int(d.strip()) for d in digitos_str.split(",") if d.strip().isdigit()]
                    else:
                        digitos = [9, 10]
                    self.config_data[self.current_mode]["nombre_archivo_digitos"] = digitos
                except:
                    self.config_data[self.current_mode]["nombre_archivo_digitos"] = [9, 10]
            
            # Guardar configuración
            self._save_config()
            
            messagebox.showinfo(
                "Configuración Guardada",
                f"La configuración para el modo {self.current_mode.upper()} ha sido guardada correctamente."
            )
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al guardar la configuración:\n{e}"
            )

