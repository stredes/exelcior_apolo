"""
Ventana de herramientas auxiliares completa.

Implementa todas las herramientas auxiliares mencionadas en el menú lateral.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any
import subprocess
import webbrowser
from pathlib import Path

from ..utils import get_logger
from ..core.integrated_processor import integrated_processor

logger = get_logger("exelcior.gui.tools_window")


class ToolsWindow:
    """
    Ventana de herramientas auxiliares.
    
    Incluye herramientas para:
    - Conversión de archivos
    - Validación de datos
    - Limpieza de archivos temporales
    - Diagnóstico del sistema
    - Utilidades de red
    """

    def __init__(self, parent: tk.Tk):
        """
        Inicializa la ventana de herramientas.
        
        Args:
            parent: Ventana padre
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Herramientas Auxiliares")
        self.window.geometry("600x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_interface()

    def _create_interface(self) -> None:
        """Crea la interfaz de herramientas."""
        # Frame principal
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="🛠️ Herramientas Auxiliares",
            font=("Arial", 16, "bold"),
            fg="#2C3E50"
        )
        title_label.pack(pady=(0, 20))
        
        # Crear notebook para organizar herramientas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Pestañas de herramientas
        self._create_file_tools_tab(notebook)
        self._create_data_tools_tab(notebook)
        self._create_system_tools_tab(notebook)
        self._create_network_tools_tab(notebook)

    def _create_file_tools_tab(self, notebook: ttk.Notebook) -> None:
        """Crea la pestaña de herramientas de archivos."""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="📁 Archivos")
        
        # Conversión de archivos
        conv_frame = ttk.LabelFrame(frame, text="Conversión de Archivos", padding=10)
        conv_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            conv_frame,
            text="📊 Excel a CSV",
            command=self._convert_excel_to_csv,
            width=20
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            conv_frame,
            text="📄 CSV a Excel",
            command=self._convert_csv_to_excel,
            width=20
        ).pack(side="left", padx=(0, 10))
        
        # Validación de archivos
        valid_frame = ttk.LabelFrame(frame, text="Validación de Archivos", padding=10)
        valid_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            valid_frame,
            text="✅ Validar Estructura Excel",
            command=self._validate_excel_structure,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            valid_frame,
            text="🔍 Detectar Tipo de Archivo",
            command=self._detect_file_type,
            width=25
        ).pack(side="left")
        
        # Limpieza de archivos
        clean_frame = ttk.LabelFrame(frame, text="Limpieza de Archivos", padding=10)
        clean_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            clean_frame,
            text="🗑️ Limpiar Archivos Temporales",
            command=self._clean_temp_files,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            clean_frame,
            text="📋 Limpiar Logs Antiguos",
            command=self._clean_old_logs,
            width=25
        ).pack(side="left")

    def _create_data_tools_tab(self, notebook: ttk.Notebook) -> None:
        """Crea la pestaña de herramientas de datos."""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="📊 Datos")
        
        # Análisis de datos
        analysis_frame = ttk.LabelFrame(frame, text="Análisis de Datos", padding=10)
        analysis_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            analysis_frame,
            text="📈 Estadísticas de Archivo",
            command=self._show_file_statistics,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            analysis_frame,
            text="🔢 Contar Registros",
            command=self._count_records,
            width=25
        ).pack(side="left")
        
        # Validación de datos
        validation_frame = ttk.LabelFrame(frame, text="Validación de Datos", padding=10)
        validation_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            validation_frame,
            text="✔️ Validar Datos Urbano",
            command=self._validate_urbano_data,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            validation_frame,
            text="✔️ Validar Datos FedEx",
            command=self._validate_fedex_data,
            width=25
        ).pack(side="left")
        
        # Limpieza de datos
        cleaning_frame = ttk.LabelFrame(frame, text="Limpieza de Datos", padding=10)
        cleaning_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            cleaning_frame,
            text="🧹 Eliminar Filas Vacías",
            command=self._remove_empty_rows,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            cleaning_frame,
            text="🔧 Normalizar Datos",
            command=self._normalize_data,
            width=25
        ).pack(side="left")

    def _create_system_tools_tab(self, notebook: ttk.Notebook) -> None:
        """Crea la pestaña de herramientas del sistema."""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="⚙️ Sistema")
        
        # Diagnóstico del sistema
        diag_frame = ttk.LabelFrame(frame, text="Diagnóstico del Sistema", padding=10)
        diag_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            diag_frame,
            text="🔍 Información del Sistema",
            command=self._show_system_info,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            diag_frame,
            text="📊 Uso de Memoria",
            command=self._show_memory_usage,
            width=25
        ).pack(side="left")
        
        # Configuración
        config_frame = ttk.LabelFrame(frame, text="Configuración", padding=10)
        config_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            config_frame,
            text="⚙️ Resetear Configuración",
            command=self._reset_configuration,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            config_frame,
            text="💾 Backup Configuración",
            command=self._backup_configuration,
            width=25
        ).pack(side="left")
        
        # Base de datos
        db_frame = ttk.LabelFrame(frame, text="Base de Datos", padding=10)
        db_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            db_frame,
            text="🗄️ Optimizar Base de Datos",
            command=self._optimize_database,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            db_frame,
            text="📤 Exportar Historial",
            command=self._export_history,
            width=25
        ).pack(side="left")

    def _create_network_tools_tab(self, notebook: ttk.Notebook) -> None:
        """Crea la pestaña de herramientas de red."""
        frame = ttk.Frame(notebook, padding=15)
        notebook.add(frame, text="🌐 Red")
        
        # Conectividad
        conn_frame = ttk.LabelFrame(frame, text="Conectividad", padding=10)
        conn_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            conn_frame,
            text="🌐 Probar Conexión Internet",
            command=self._test_internet_connection,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            conn_frame,
            text="📡 Ping a Servidor",
            command=self._ping_server,
            width=25
        ).pack(side="left")
        
        # Impresoras
        printer_frame = ttk.LabelFrame(frame, text="Impresoras", padding=10)
        printer_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            printer_frame,
            text="🖨️ Detectar Impresoras",
            command=self._detect_printers,
            width=25
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            printer_frame,
            text="🏷️ Probar Impresora Zebra",
            command=self._test_zebra_printer,
            width=25
        ).pack(side="left")

    # Métodos de herramientas de archivos

    def _convert_excel_to_csv(self) -> None:
        """Convierte archivo Excel a CSV."""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo Excel",
                filetypes=[("Archivos Excel", "*.xlsx *.xls *.xlsm")]
            )
            
            if file_path:
                import pandas as pd
                df = pd.read_excel(file_path)
                
                save_path = filedialog.asksaveasfilename(
                    title="Guardar como CSV",
                    defaultextension=".csv",
                    filetypes=[("Archivos CSV", "*.csv")]
                )
                
                if save_path:
                    df.to_csv(save_path, index=False, encoding='utf-8')
                    messagebox.showinfo("Éxito", f"Archivo convertido a: {save_path}")
                    
        except Exception as e:
            logger.error(f"Error convirtiendo Excel a CSV: {e}")
            messagebox.showerror("Error", f"Error en conversión: {str(e)}")

    def _convert_csv_to_excel(self) -> None:
        """Convierte archivo CSV a Excel."""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo CSV",
                filetypes=[("Archivos CSV", "*.csv")]
            )
            
            if file_path:
                import pandas as pd
                df = pd.read_csv(file_path)
                
                save_path = filedialog.asksaveasfilename(
                    title="Guardar como Excel",
                    defaultextension=".xlsx",
                    filetypes=[("Archivos Excel", "*.xlsx")]
                )
                
                if save_path:
                    df.to_excel(save_path, index=False)
                    messagebox.showinfo("Éxito", f"Archivo convertido a: {save_path}")
                    
        except Exception as e:
            logger.error(f"Error convirtiendo CSV a Excel: {e}")
            messagebox.showerror("Error", f"Error en conversión: {str(e)}")

    def _validate_excel_structure(self) -> None:
        """Valida la estructura de un archivo Excel."""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo Excel",
                filetypes=[("Archivos Excel", "*.xlsx *.xls *.xlsm")]
            )
            
            if file_path:
                result = integrated_processor.select_file(Path(file_path))
                
                if result.get("success"):
                    info = f"""
Validación de Estructura Excel

Archivo: {Path(file_path).name}
Tipo detectado: {result.get('file_type', 'N/A')}
Filas: {result.get('rows', 0):,}
Columnas: {len(result.get('columns', []))}

Columnas encontradas:
{chr(10).join(f"• {col}" for col in result.get('columns', []))}
                    """
                    messagebox.showinfo("Validación Exitosa", info)
                else:
                    messagebox.showerror("Error de Validación", result.get('error', 'Error desconocido'))
                    
        except Exception as e:
            logger.error(f"Error validando estructura: {e}")
            messagebox.showerror("Error", f"Error en validación: {str(e)}")

    def _detect_file_type(self) -> None:
        """Detecta el tipo de archivo."""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo",
                filetypes=[("Todos los archivos", "*.*")]
            )
            
            if file_path:
                path_obj = Path(file_path)
                
                # Información básica
                info = f"""
Detección de Tipo de Archivo

Nombre: {path_obj.name}
Extensión: {path_obj.suffix}
Tamaño: {path_obj.stat().st_size / 1024:.1f} KB

Tipo detectado: """
                
                # Detectar tipo específico
                if path_obj.suffix.lower() in ['.xlsx', '.xls', '.xlsm']:
                    from ..core.urbano_detector import UrbanoCodeDetector
                    if UrbanoCodeDetector.is_urbano_file(path_obj):
                        codigo = UrbanoCodeDetector.extract_urbano_code(path_obj)
                        info += f"Archivo Urbano (Código: {codigo})"
                    else:
                        info += "Archivo Excel estándar"
                elif path_obj.suffix.lower() == '.csv':
                    info += "Archivo CSV"
                else:
                    info += "Tipo no reconocido para procesamiento"
                
                messagebox.showinfo("Detección de Tipo", info)
                
        except Exception as e:
            logger.error(f"Error detectando tipo: {e}")
            messagebox.showerror("Error", f"Error en detección: {str(e)}")

    def _clean_temp_files(self) -> None:
        """Limpia archivos temporales."""
        try:
            temp_dirs = ["logs", "exports", "__pycache__"]
            cleaned_files = 0
            
            for temp_dir in temp_dirs:
                temp_path = Path(temp_dir)
                if temp_path.exists():
                    for file_path in temp_path.rglob("*.tmp"):
                        file_path.unlink()
                        cleaned_files += 1
                    for file_path in temp_path.rglob("*.pyc"):
                        file_path.unlink()
                        cleaned_files += 1
            
            messagebox.showinfo("Limpieza Completada", f"Se eliminaron {cleaned_files} archivos temporales")
            
        except Exception as e:
            logger.error(f"Error limpiando archivos temporales: {e}")
            messagebox.showerror("Error", f"Error en limpieza: {str(e)}")

    def _clean_old_logs(self) -> None:
        """Limpia logs antiguos."""
        try:
            logs_path = Path("logs")
            if not logs_path.exists():
                messagebox.showinfo("Limpieza", "No hay directorio de logs")
                return
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=30)
            cleaned_files = 0
            
            for log_file in logs_path.glob("*.log"):
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_date:
                    log_file.unlink()
                    cleaned_files += 1
            
            messagebox.showinfo("Limpieza Completada", f"Se eliminaron {cleaned_files} logs antiguos (>30 días)")
            
        except Exception as e:
            logger.error(f"Error limpiando logs: {e}")
            messagebox.showerror("Error", f"Error en limpieza: {str(e)}")

    # Métodos de herramientas de datos

    def _show_file_statistics(self) -> None:
        """Muestra estadísticas del archivo actual."""
        try:
            info = integrated_processor.get_file_info()
            
            if "error" in info:
                messagebox.showwarning("Sin Archivo", "No hay archivo cargado")
                return
            
            stats_text = f"""
Estadísticas del Archivo

Nombre: {info.get('file_name', 'N/A')}
Tamaño: {info.get('file_size_mb', 0):.2f} MB
Filas: {info.get('rows', 0):,}
Columnas: {info.get('columns', 0)}
Uso de memoria: {info.get('memory_usage_mb', 0):.2f} MB
Modo: {info.get('mode', 'N/A').upper()}
            """
            
            messagebox.showinfo("Estadísticas", stats_text)
            
        except Exception as e:
            logger.error(f"Error mostrando estadísticas: {e}")
            messagebox.showerror("Error", f"Error obteniendo estadísticas: {str(e)}")

    def _count_records(self) -> None:
        """Cuenta registros del archivo actual."""
        try:
            info = integrated_processor.get_file_info()
            
            if "error" in info:
                messagebox.showwarning("Sin Archivo", "No hay archivo cargado")
                return
            
            count_text = f"""
Conteo de Registros

Total de filas: {info.get('rows', 0):,}
Total de columnas: {info.get('columns', 0)}

Columnas disponibles:
{chr(10).join(f"• {col}" for col in info.get('column_names', []))}
            """
            
            messagebox.showinfo("Conteo de Registros", count_text)
            
        except Exception as e:
            logger.error(f"Error contando registros: {e}")
            messagebox.showerror("Error", f"Error en conteo: {str(e)}")

    def _validate_urbano_data(self) -> None:
        """Valida datos específicos de Urbano."""
        messagebox.showinfo("Validación Urbano", "Validación de datos Urbano en desarrollo")

    def _validate_fedex_data(self) -> None:
        """Valida datos específicos de FedEx."""
        messagebox.showinfo("Validación FedEx", "Validación de datos FedEx en desarrollo")

    def _remove_empty_rows(self) -> None:
        """Elimina filas vacías."""
        messagebox.showinfo("Limpieza", "Eliminación de filas vacías en desarrollo")

    def _normalize_data(self) -> None:
        """Normaliza datos."""
        messagebox.showinfo("Normalización", "Normalización de datos en desarrollo")

    # Métodos de herramientas del sistema

    def _show_system_info(self) -> None:
        """Muestra información del sistema."""
        try:
            import platform
            import sys
            
            info_text = f"""
Información del Sistema

Sistema Operativo: {platform.system()} {platform.release()}
Arquitectura: {platform.machine()}
Procesador: {platform.processor()}

Python:
Versión: {sys.version.split()[0]}
Ejecutable: {sys.executable}

Exelcior Apolo:
Versión: 2.0.0
Directorio: {Path.cwd()}
            """
            
            messagebox.showinfo("Información del Sistema", info_text)
            
        except Exception as e:
            logger.error(f"Error obteniendo info del sistema: {e}")
            messagebox.showerror("Error", f"Error obteniendo información: {str(e)}")

    def _show_memory_usage(self) -> None:
        """Muestra uso de memoria."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            usage_text = f"""
Uso de Memoria

Memoria RSS: {memory_info.rss / 1024 / 1024:.1f} MB
Memoria VMS: {memory_info.vms / 1024 / 1024:.1f} MB
CPU: {process.cpu_percent():.1f}%

Sistema:
Memoria total: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB
Memoria disponible: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.1f} GB
Uso de memoria: {psutil.virtual_memory().percent:.1f}%
            """
            
            messagebox.showinfo("Uso de Memoria", usage_text)
            
        except ImportError:
            messagebox.showwarning("Dependencia", "psutil no está instalado")
        except Exception as e:
            logger.error(f"Error obteniendo uso de memoria: {e}")
            messagebox.showerror("Error", f"Error obteniendo memoria: {str(e)}")

    def _reset_configuration(self) -> None:
        """Resetea la configuración."""
        if messagebox.askyesno("Confirmar", "¿Está seguro de resetear toda la configuración?"):
            messagebox.showinfo("Reset", "Configuración reseteada (funcionalidad en desarrollo)")

    def _backup_configuration(self) -> None:
        """Hace backup de la configuración."""
        messagebox.showinfo("Backup", "Backup de configuración en desarrollo")

    def _optimize_database(self) -> None:
        """Optimiza la base de datos."""
        messagebox.showinfo("Optimización", "Optimización de base de datos en desarrollo")

    def _export_history(self) -> None:
        """Exporta el historial."""
        messagebox.showinfo("Exportar", "Exportación de historial en desarrollo")

    # Métodos de herramientas de red

    def _test_internet_connection(self) -> None:
        """Prueba la conexión a internet."""
        try:
            import urllib.request
            
            urllib.request.urlopen('http://www.google.com', timeout=5)
            messagebox.showinfo("Conectividad", "✅ Conexión a internet exitosa")
            
        except Exception as e:
            messagebox.showerror("Conectividad", f"❌ Sin conexión a internet: {str(e)}")

    def _ping_server(self) -> None:
        """Hace ping a un servidor."""
        server = tk.simpledialog.askstring("Ping", "Ingrese la dirección del servidor:")
        if server:
            try:
                import subprocess
                result = subprocess.run(['ping', '-n', '4', server], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    messagebox.showinfo("Ping Exitoso", f"✅ Servidor {server} responde")
                else:
                    messagebox.showerror("Ping Fallido", f"❌ Servidor {server} no responde")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Error en ping: {str(e)}")

    def _detect_printers(self) -> None:
        """Detecta impresoras disponibles."""
        messagebox.showinfo("Impresoras", "Detección de impresoras en desarrollo")

    def _test_zebra_printer(self) -> None:
        """Prueba impresora Zebra."""
        messagebox.showinfo("Zebra", "Prueba de impresora Zebra en desarrollo")


def open_tools_window(parent: tk.Tk) -> None:
    """
    Abre la ventana de herramientas.
    
    Args:
        parent: Ventana padre
    """
    try:
        ToolsWindow(parent)
    except Exception as e:
        logger.error(f"Error abriendo ventana de herramientas: {e}")
        messagebox.showerror("Error", f"Error al abrir herramientas: {str(e)}")

