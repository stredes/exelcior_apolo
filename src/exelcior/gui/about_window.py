"""
Ventana "Acerca de" con información completa de la aplicación.
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
from datetime import datetime

from ..utils import get_logger

logger = get_logger("exelcior.gui.about_window")


class AboutWindow:
    """Ventana de información sobre la aplicación."""

    def __init__(self, parent: tk.Tk):
        """
        Inicializa la ventana Acerca de.
        
        Args:
            parent: Ventana padre
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Acerca de Exelcior Apolo")
        self.window.geometry("500x600")
        self.window.transient(parent)
        self.window.resizable(False, False)
        
        self._create_interface()

    def _create_interface(self) -> None:
        """Crea la interfaz de la ventana."""
        # Frame principal
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Logo y título
        self._create_header(main_frame)
        
        # Información principal
        self._create_info_section(main_frame)
        
        # Características
        self._create_features_section(main_frame)
        
        # Información técnica
        self._create_technical_section(main_frame)
        
        # Botones
        self._create_buttons_section(main_frame)

    def _create_header(self, parent: ttk.Frame) -> None:
        """Crea el encabezado con logo y título."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Título principal
        title_label = tk.Label(
            header_frame,
            text="🚀 Exelcior Apolo",
            font=("Arial", 24, "bold"),
            fg="#2C3E50"
        )
        title_label.pack()
        
        # Subtítulo
        subtitle_label = tk.Label(
            header_frame,
            text="Transformador Excel Profesional",
            font=("Arial", 12),
            fg="#7F8C8D"
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Versión
        version_label = tk.Label(
            header_frame,
            text="Versión 2.0.0",
            font=("Arial", 10, "bold"),
            fg="#E74C3C"
        )
        version_label.pack(pady=(5, 0))

    def _create_info_section(self, parent: ttk.Frame) -> None:
        """Crea la sección de información principal."""
        info_frame = ttk.LabelFrame(parent, text="Información General", padding=15)
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_text = """
Exelcior Apolo es una aplicación profesional diseñada para el procesamiento 
inteligente de archivos Excel con múltiples modos de operación.

Desarrollada específicamente para optimizar flujos de trabajo logísticos 
y de gestión de datos, ofreciendo herramientas avanzadas de transformación, 
validación y exportación.
        """
        
        info_label = tk.Label(
            info_frame,
            text=info_text.strip(),
            font=("Arial", 10),
            justify="left",
            wraplength=450
        )
        info_label.pack(anchor="w")

    def _create_features_section(self, parent: ttk.Frame) -> None:
        """Crea la sección de características."""
        features_frame = ttk.LabelFrame(parent, text="Características Principales", padding=15)
        features_frame.pack(fill="x", pady=(0, 15))
        
        features = [
            "✅ Procesamiento automático de archivos FedEx, Urbano y Listados",
            "✅ Detección inteligente de tipos de archivo por nombre",
            "✅ Sistema de configuración avanzado y personalizable",
            "✅ Validación robusta de datos con reportes detallados",
            "✅ Exportación a PDF con formato profesional",
            "✅ Búsqueda de códigos postales por comuna",
            "✅ Editor de etiquetas Zebra integrado",
            "✅ Historial completo de operaciones",
            "✅ Herramientas auxiliares especializadas",
            "✅ Interfaz intuitiva y moderna"
        ]
        
        for feature in features:
            feature_label = tk.Label(
                features_frame,
                text=feature,
                font=("Arial", 9),
                anchor="w"
            )
            feature_label.pack(fill="x", pady=1)

    def _create_technical_section(self, parent: ttk.Frame) -> None:
        """Crea la sección de información técnica."""
        tech_frame = ttk.LabelFrame(parent, text="Información Técnica", padding=15)
        tech_frame.pack(fill="x", pady=(0, 15))
        
        # Crear dos columnas
        columns_frame = ttk.Frame(tech_frame)
        columns_frame.pack(fill="x")
        
        # Columna izquierda
        left_frame = ttk.Frame(columns_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        
        left_info = [
            "🐍 Python 3.11+",
            "📊 Pandas & NumPy",
            "🖼️ Tkinter GUI",
            "🗄️ SQLAlchemy ORM",
            "📄 ReportLab PDF"
        ]
        
        for info in left_info:
            tk.Label(left_frame, text=info, font=("Arial", 9), anchor="w").pack(fill="x", pady=1)
        
        # Columna derecha
        right_frame = ttk.Frame(columns_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        
        right_info = [
            "📈 OpenPyXL Excel",
            "🏷️ Zebra Printing",
            "🔍 Búsqueda Avanzada",
            "⚡ Procesamiento Asíncrono",
            "🛡️ Validación Robusta"
        ]
        
        for info in right_info:
            tk.Label(right_frame, text=info, font=("Arial", 9), anchor="w").pack(fill="x", pady=1)

    def _create_buttons_section(self, parent: ttk.Frame) -> None:
        """Crea la sección de botones."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill="x", pady=(15, 0))
        
        # Información de copyright
        copyright_label = tk.Label(
            buttons_frame,
            text=f"© {datetime.now().year} Exelcior Apolo. Todos los derechos reservados.",
            font=("Arial", 8),
            fg="#95A5A6"
        )
        copyright_label.pack(pady=(0, 15))
        
        # Botones de acción
        action_frame = ttk.Frame(buttons_frame)
        action_frame.pack()
        
        ttk.Button(
            action_frame,
            text="📋 Copiar Info del Sistema",
            command=self._copy_system_info,
            width=20
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            action_frame,
            text="❌ Cerrar",
            command=self.window.destroy,
            width=10
        ).pack(side="left")

    def _copy_system_info(self) -> None:
        """Copia información del sistema al portapapeles."""
        try:
            import platform
            import sys
            
            system_info = f"""
Exelcior Apolo v2.0.0
Sistema Operativo: {platform.system()} {platform.release()}
Arquitectura: {platform.machine()}
Python: {sys.version.split()[0]}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            self.window.clipboard_clear()
            self.window.clipboard_append(system_info)
            
            # Mostrar confirmación temporal
            temp_label = tk.Label(
                self.window,
                text="✅ Información copiada al portapapeles",
                fg="green",
                font=("Arial", 9)
            )
            temp_label.place(relx=0.5, rely=0.9, anchor="center")
            
            # Eliminar después de 2 segundos
            self.window.after(2000, temp_label.destroy)
            
        except Exception as e:
            logger.error(f"Error copiando información: {e}")


def show_about_window(parent: tk.Tk) -> None:
    """
    Muestra la ventana Acerca de.
    
    Args:
        parent: Ventana padre
    """
    try:
        AboutWindow(parent)
    except Exception as e:
        logger.error(f"Error mostrando ventana Acerca de: {e}")
        tk.messagebox.showerror("Error", f"Error al mostrar información: {str(e)}")

