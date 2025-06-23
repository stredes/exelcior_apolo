"""
Ventana de consulta por código de rastreo.

Permite buscar y consultar códigos de rastreo en la base de datos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List
import re

from ..utils import get_logger
from ..database.manager import DatabaseManager

logger = get_logger("exelcior.gui.code_search_window")


class CodeSearchWindow:
    """
    Ventana de consulta por código de rastreo.
    
    Permite buscar códigos de rastreo y mostrar información detallada.
    """

    def __init__(self, parent: tk.Tk):
        """
        Inicializa la ventana de consulta por código.
        
        Args:
            parent: Ventana padre
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("🔍 Consulta por Código")
        self.window.geometry("700x500")
        self.window.transient(parent)
        
        self.db_manager = DatabaseManager()
        
        self._create_interface()

    def _create_interface(self) -> None:
        """Crea la interfaz de consulta."""
        # Frame principal
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="🔍 Consulta por Código de Rastreo",
            font=("Arial", 16, "bold"),
            fg="#2C3E50"
        )
        title_label.pack(pady=(0, 20))
        
        # Frame de búsqueda
        self._create_search_frame(main_frame)
        
        # Frame de resultados
        self._create_results_frame(main_frame)
        
        # Frame de botones
        self._create_buttons_frame(main_frame)

    def _create_search_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de búsqueda."""
        search_frame = ttk.LabelFrame(parent, text="Búsqueda de Código", padding=15)
        search_frame.pack(fill="x", pady=(0, 15))
        
        # Campo de búsqueda
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(search_input_frame, text="Código de Rastreo:").pack(side="left", padx=(0, 10))
        
        self.code_var = tk.StringVar()
        code_entry = ttk.Entry(search_input_frame, textvariable=self.code_var, width=30, font=("Arial", 11))
        code_entry.pack(side="left", padx=(0, 10))
        code_entry.bind("<Return>", lambda e: self._search_code())
        code_entry.focus()
        
        ttk.Button(search_input_frame, text="🔍 Buscar", command=self._search_code, width=10).pack(side="left", padx=(0, 5))
        ttk.Button(search_input_frame, text="🔄 Limpiar", command=self._clear_search, width=10).pack(side="left")
        
        # Opciones de búsqueda
        options_frame = ttk.Frame(search_frame)
        options_frame.pack(fill="x")
        
        self.exact_match_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Búsqueda exacta", variable=self.exact_match_var).pack(side="left", padx=(0, 15))
        
        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Sensible a mayúsculas", variable=self.case_sensitive_var).pack(side="left", padx=(0, 15))
        
        # Tipos de código
        ttk.Label(options_frame, text="Tipo:").pack(side="left", padx=(15, 5))
        self.code_type_var = tk.StringVar()
        type_combo = ttk.Combobox(
            options_frame,
            textvariable=self.code_type_var,
            values=["Todos", "FedEx", "Urbano", "Tracking", "Guía"],
            width=10,
            state="readonly"
        )
        type_combo.set("Todos")
        type_combo.pack(side="left")

    def _create_results_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de resultados."""
        results_frame = ttk.LabelFrame(parent, text="Resultados", padding=15)
        results_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Tabla de resultados
        columns = ("Código", "Tipo", "Fecha", "Cliente", "Ciudad", "Estado", "Referencia")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=12)
        
        # Configurar columnas
        column_widths = {
            "Código": 120,
            "Tipo": 80,
            "Fecha": 100,
            "Cliente": 150,
            "Ciudad": 120,
            "Estado": 100,
            "Referencia": 100
        }
        
        for col in columns:
            self.results_tree.heading(col, text=col, command=lambda c=col: self._sort_results(c))
            self.results_tree.column(col, width=column_widths.get(col, 100), anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack elementos
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.results_tree.pack(side="left", fill="both", expand=True)
        
        # Eventos
        self.results_tree.bind("<Double-1>", self._on_double_click)
        
        # Información de resultados
        self.results_info_label = tk.Label(results_frame, text="", fg="#666666")
        self.results_info_label.pack(side="bottom", anchor="w", pady=(5, 0))

    def _create_buttons_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de botones."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill="x")
        
        ttk.Button(buttons_frame, text="📄 Ver Detalles", command=self._view_details, width=15).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="📋 Copiar Código", command=self._copy_code, width=15).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="📤 Exportar", command=self._export_results, width=12).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="❌ Cerrar", command=self.window.destroy, width=10).pack(side="right")

    def _search_code(self) -> None:
        """Realiza la búsqueda del código."""
        try:
            search_code = self.code_var.get().strip()
            
            if not search_code:
                messagebox.showwarning("Búsqueda", "Ingrese un código para buscar")
                return
            
            # Validar formato del código
            if not self._validate_code_format(search_code):
                messagebox.showwarning("Formato", "El formato del código no es válido")
                return
            
            # Limpiar resultados anteriores
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Realizar búsqueda
            results = self._perform_search(search_code)
            
            # Mostrar resultados
            if results:
                for result in results:
                    self.results_tree.insert("", "end", values=result)
                
                self.results_info_label.config(text=f"Se encontraron {len(results)} resultado(s)")
            else:
                self.results_info_label.config(text="No se encontraron resultados")
                messagebox.showinfo("Sin resultados", f"No se encontró el código: {search_code}")
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            messagebox.showerror("Error", f"Error al buscar código: {str(e)}")

    def _validate_code_format(self, code: str) -> bool:
        """Valida el formato del código."""
        try:
            # Patrones comunes de códigos de rastreo
            patterns = [
                r'^\d{12}$',  # FedEx: 12 dígitos
                r'^WYB\d{9}$',  # Urbano: WYB + 9 dígitos
                r'^\d{9}$',  # Urbano: 9 dígitos
                r'^[A-Z]{2}\d{9}[A-Z]{2}$',  # Formato internacional
                r'^[0-9A-Z]{8,20}$',  # Formato general alfanumérico
            ]
            
            for pattern in patterns:
                if re.match(pattern, code.upper()):
                    return True
            
            # Si no coincide con patrones específicos, permitir búsqueda general
            return len(code) >= 3
            
        except Exception:
            return False

    def _perform_search(self, search_code: str) -> List[tuple]:
        """Realiza la búsqueda en la base de datos."""
        try:
            # Simular búsqueda en base de datos
            # En implementación real, esto consultaría la base de datos
            
            sample_data = [
                ("882121206110", "FedEx", "2025-06-18", "A Y R salud integral spa", "VALDIVIA", "Entregado", "1844"),
                ("882121691254", "FedEx", "2025-06-18", "LABORATORIO CLINICO BIOMAAS LTD", "SAN FERNANDO", "En tránsito", "55752"),
                ("882122200303", "FedEx", "2025-06-18", "ILUSTRE MUNICIPALIDAD DE QUILLOT", "QUILLOTA", "Entregado", "55749"),
                ("882129230583", "FedEx", "2025-06-18", "CORPORACION MUNICIPAL DE CALAM", "CALAMA", "Pendiente", "55772"),
                ("WYB203950845", "Urbano", "2025-06-20", "clinicad dental san martin", "CONCEPCION", "Entregado", "4038"),
                ("WYB203954352", "Urbano", "2025-06-20", "CONTRERAS Y PEREZ SPA", "PICHILEMU", "En tránsito", "55767"),
                ("192403809", "Urbano", "2025-06-23", "VARIOS CLIENTES", "MULTIPLE", "Procesado", "LOTE"),
            ]
            
            # Filtrar resultados según búsqueda
            results = []
            search_upper = search_code.upper()
            exact_match = self.exact_match_var.get()
            case_sensitive = self.case_sensitive_var.get()
            code_type = self.code_type_var.get()
            
            for record in sample_data:
                code = record[0] if case_sensitive else record[0].upper()
                search_term = search_code if case_sensitive else search_upper
                
                # Filtro por tipo
                if code_type != "Todos" and record[1] != code_type:
                    continue
                
                # Filtro por código
                if exact_match:
                    if code == search_term:
                        results.append(record)
                else:
                    if search_term in code:
                        results.append(record)
            
            return results
            
        except Exception as e:
            logger.error(f"Error realizando búsqueda: {e}")
            return []

    def _clear_search(self) -> None:
        """Limpia la búsqueda."""
        self.code_var.set("")
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.results_info_label.config(text="")

    def _sort_results(self, column: str) -> None:
        """Ordena los resultados por columna."""
        try:
            # Obtener datos actuales
            data = [(self.results_tree.set(child, column), child) for child in self.results_tree.get_children("")]
            
            # Ordenar
            data.sort(reverse=False)
            
            # Reorganizar elementos
            for index, (val, child) in enumerate(data):
                self.results_tree.move(child, "", index)
                
        except Exception as e:
            logger.error(f"Error ordenando resultados: {e}")

    def _on_double_click(self, event) -> None:
        """Maneja doble click en resultado."""
        self._view_details()

    def _view_details(self) -> None:
        """Muestra detalles del código seleccionado."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Seleccione un resultado para ver detalles")
            return
        
        # Obtener datos del resultado
        item = selection[0]
        values = self.results_tree.item(item, "values")
        
        # Crear ventana de detalles
        details_window = tk.Toplevel(self.window)
        details_window.title("Detalles del Código")
        details_window.geometry("500x600")
        details_window.transient(self.window)
        
        # Contenido de detalles
        details_frame = ttk.Frame(details_window, padding=20)
        details_frame.pack(fill="both", expand=True)
        
        tk.Label(details_frame, text="📦 Detalles del Envío", font=("Arial", 14, "bold")).pack(pady=(0, 15))
        
        # Información principal
        info_frame = ttk.LabelFrame(details_frame, text="Información Principal", padding=15)
        info_frame.pack(fill="x", pady=(0, 15))
        
        details_info = [
            ("Código de Rastreo:", values[0]),
            ("Tipo de Servicio:", values[1]),
            ("Fecha de Envío:", values[2]),
            ("Cliente/Destinatario:", values[3]),
            ("Ciudad de Destino:", values[4]),
            ("Estado Actual:", values[5]),
            ("Referencia:", values[6])
        ]
        
        for label, value in details_info:
            row_frame = ttk.Frame(info_frame)
            row_frame.pack(fill="x", pady=2)
            
            tk.Label(row_frame, text=label, font=("Arial", 10, "bold"), width=20, anchor="w").pack(side="left")
            tk.Label(row_frame, text=value, font=("Arial", 10), anchor="w").pack(side="left", padx=(10, 0))
        
        # Historial de seguimiento
        tracking_frame = ttk.LabelFrame(details_frame, text="Historial de Seguimiento", padding=15)
        tracking_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Simular historial
        tracking_data = [
            ("2025-06-23 10:30", "Entregado", "Paquete entregado al destinatario"),
            ("2025-06-23 08:15", "En reparto", "Paquete en vehículo de reparto"),
            ("2025-06-22 16:45", "En centro de distribución", "Llegada a centro local"),
            ("2025-06-22 14:20", "En tránsito", "Paquete en ruta"),
            ("2025-06-21 09:00", "Recolectado", "Paquete recolectado del origen")
        ]
        
        tracking_tree = ttk.Treeview(tracking_frame, columns=("Fecha", "Estado", "Descripción"), show="headings", height=8)
        tracking_tree.heading("Fecha", text="Fecha/Hora")
        tracking_tree.heading("Estado", text="Estado")
        tracking_tree.heading("Descripción", text="Descripción")
        
        tracking_tree.column("Fecha", width=120)
        tracking_tree.column("Estado", width=100)
        tracking_tree.column("Descripción", width=250)
        
        for track_info in tracking_data:
            tracking_tree.insert("", "end", values=track_info)
        
        tracking_tree.pack(fill="both", expand=True)
        
        # Botones
        buttons_frame = ttk.Frame(details_frame)
        buttons_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(buttons_frame, text="📋 Copiar Código", command=lambda: self._copy_to_clipboard(values[0])).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="🖨️ Imprimir", command=lambda: messagebox.showinfo("Impresión", "Funcionalidad en desarrollo")).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="❌ Cerrar", command=details_window.destroy).pack(side="right")

    def _copy_code(self) -> None:
        """Copia el código seleccionado al portapapeles."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Seleccione un resultado para copiar")
            return
        
        item = selection[0]
        code = self.results_tree.item(item, "values")[0]
        self._copy_to_clipboard(code)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copia texto al portapapeles."""
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            messagebox.showinfo("Copiado", f"Código copiado: {text}")
        except Exception as e:
            logger.error(f"Error copiando al portapapeles: {e}")

    def _export_results(self) -> None:
        """Exporta los resultados."""
        try:
            from tkinter import filedialog
            import csv
            
            if not self.results_tree.get_children():
                messagebox.showwarning("Sin datos", "No hay resultados para exportar")
                return
            
            file_path = filedialog.asksaveasfilename(
                title="Exportar Resultados",
                defaultextension=".csv",
                filetypes=[("Archivos CSV", "*.csv"), ("Archivos Excel", "*.xlsx")]
            )
            
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Escribir encabezados
                    headers = ["Código", "Tipo", "Fecha", "Cliente", "Ciudad", "Estado", "Referencia"]
                    writer.writerow(headers)
                    
                    # Escribir datos
                    for item in self.results_tree.get_children():
                        values = self.results_tree.item(item, "values")
                        writer.writerow(values)
                
                messagebox.showinfo("Éxito", f"Resultados exportados a: {file_path}")
                
        except Exception as e:
            logger.error(f"Error exportando resultados: {e}")
            messagebox.showerror("Error", f"Error al exportar: {str(e)}")


def open_code_search_window(parent: tk.Tk) -> None:
    """
    Abre la ventana de consulta por código.
    
    Args:
        parent: Ventana padre
    """
    try:
        CodeSearchWindow(parent)
    except Exception as e:
        logger.error(f"Error abriendo ventana de consulta: {e}")
        messagebox.showerror("Error", f"Error al abrir consulta: {str(e)}")

