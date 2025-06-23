"""
Vista de datos con tabla completa y funcional.

Implementa la vista de datos que se muestra en las capturas de pantalla.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List
import pandas as pd
from pathlib import Path

from ..utils import get_logger

logger = get_logger("exelcior.gui.data_view")


class DataViewWindow:
    """
    Ventana de vista de datos con tabla completa.
    
    Muestra los datos procesados en una tabla con funcionalidades de:
    - Visualización completa de datos
    - Filtrado y búsqueda
    - Selección múltiple
    - Eliminación de filas
    - Exportación
    - Impresión
    """

    def __init__(self, parent: tk.Tk, dataframe: pd.DataFrame, title: str = "Vista Previa"):
        """
        Inicializa la vista de datos.
        
        Args:
            parent: Ventana padre
            dataframe: DataFrame con los datos a mostrar
            title: Título de la ventana
        """
        self.parent = parent
        self.df = dataframe.copy()
        self.original_df = dataframe.copy()
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("1200x700")
        self.window.transient(parent)
        
        self.selected_rows = set()
        
        self._create_interface()
        self._load_data()

    def _create_interface(self) -> None:
        """Crea la interfaz de la vista de datos."""
        # Frame principal
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Frame superior con controles
        self._create_controls_frame(main_frame)
        
        # Frame de la tabla
        self._create_table_frame(main_frame)
        
        # Frame inferior con información y botones
        self._create_bottom_frame(main_frame)

    def _create_controls_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de controles superiores."""
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill="x", pady=(0, 10))
        
        # Búsqueda
        search_frame = ttk.LabelFrame(controls_frame, text="Búsqueda y Filtros", padding=5)
        search_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Campo de búsqueda
        ttk.Label(search_frame, text="Buscar:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=(0, 10))
        search_entry.bind("<KeyRelease>", self._on_search_change)
        
        # Filtro por columna
        ttk.Label(search_frame, text="Columna:").pack(side="left", padx=(0, 5))
        self.column_var = tk.StringVar()
        self.column_combo = ttk.Combobox(search_frame, textvariable=self.column_var, width=15, state="readonly")
        self.column_combo.pack(side="left", padx=(0, 10))
        
        # Botones de filtro
        ttk.Button(search_frame, text="🔍", command=self._apply_search, width=3).pack(side="left", padx=(0, 5))
        ttk.Button(search_frame, text="🔄", command=self._clear_search, width=3).pack(side="left")
        
        # Controles de selección
        selection_frame = ttk.LabelFrame(controls_frame, text="Selección", padding=5)
        selection_frame.pack(side="right")
        
        ttk.Button(selection_frame, text="✅ Seleccionar Todo", command=self._select_all, width=15).pack(side="left", padx=(0, 5))
        ttk.Button(selection_frame, text="❌ Deseleccionar", command=self._deselect_all, width=15).pack(side="left")

    def _create_table_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de la tabla."""
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Crear Treeview con columnas dinámicas
        self.columns = list(self.df.columns)
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=20)
        
        # Configurar columnas
        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            # Ajustar ancho según contenido
            max_width = max(len(str(col)) * 8, 80)
            if len(self.df) > 0:
                sample_values = self.df[col].astype(str).head(10)
                if not sample_values.empty:
                    max_content_width = max(len(str(val)) * 7 for val in sample_values)
                    max_width = min(max(max_width, max_content_width), 200)
            
            self.tree.column(col, width=max_width, anchor="w")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack elementos
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Eventos
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Control-Button-1>", self._on_ctrl_click)
        self.tree.bind("<Shift-Button-1>", self._on_shift_click)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _create_bottom_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame inferior con información y botones."""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill="x")
        
        # Información
        info_frame = ttk.Frame(bottom_frame)
        info_frame.pack(side="left", fill="x", expand=True)
        
        self.info_label = tk.Label(info_frame, text="", fg="#666666", anchor="w")
        self.info_label.pack(side="left")
        
        # Botones de acción
        buttons_frame = ttk.Frame(bottom_frame)
        buttons_frame.pack(side="right")
        
        ttk.Button(buttons_frame, text="🖨️ Imprimir", command=self._print_data, width=12).pack(side="left", padx=(0, 5))
        ttk.Button(buttons_frame, text="❌ Cerrar", command=self._close_window, width=10).pack(side="left", padx=(0, 5))
        ttk.Button(buttons_frame, text="🗑️ Eliminar filas seleccionadas", command=self._delete_selected, width=25).pack(side="left", padx=(0, 5))
        
        # Información de totales (como en la captura)
        self.totals_label = tk.Label(bottom_frame, text="", font=("Arial", 10, "bold"), fg="#2C3E50")
        self.totals_label.pack(side="bottom", anchor="e", pady=(5, 0))

    def _load_data(self) -> None:
        """Carga los datos en la tabla."""
        try:
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Actualizar combobox de columnas
            self.column_combo['values'] = ["Todas"] + list(self.df.columns)
            self.column_combo.set("Todas")
            
            # Cargar datos
            for index, row in self.df.iterrows():
                values = []
                for col in self.columns:
                    value = row[col]
                    # Formatear valores para mostrar
                    if pd.isna(value):
                        values.append("")
                    elif isinstance(value, float):
                        values.append(f"{value:.2f}" if value != int(value) else str(int(value)))
                    else:
                        values.append(str(value))
                
                item_id = self.tree.insert("", "end", values=values, tags=(str(index),))
            
            self._update_info()
            self._calculate_totals()
            
        except Exception as e:
            logger.error(f"Error cargando datos: {e}")
            messagebox.showerror("Error", f"Error al cargar datos: {str(e)}")

    def _update_info(self) -> None:
        """Actualiza la información mostrada."""
        total_rows = len(self.df)
        displayed_rows = len(self.tree.get_children())
        selected_count = len(self.selected_rows)
        
        info_text = f"Mostrando {displayed_rows} de {total_rows} filas, {len(self.columns)} columnas"
        if selected_count > 0:
            info_text += f" | {selected_count} seleccionadas"
        
        self.info_label.config(text=info_text)

    def _calculate_totals(self) -> None:
        """Calcula y muestra totales como en la captura."""
        try:
            # Buscar columnas numéricas para calcular totales
            numeric_columns = []
            for col in self.df.columns:
                if self.df[col].dtype in ['int64', 'float64'] or col.upper() in ['BULTOS', 'PIEZAS', 'CANTIDAD', 'TOTAL']:
                    numeric_columns.append(col)
            
            if numeric_columns:
                # Calcular total de la primera columna numérica encontrada
                main_col = numeric_columns[0]
                total_value = self.df[main_col].sum()
                
                # Formato como en la captura: "Total BULTOS: 67"
                totals_text = f"Total {main_col.upper()}: {total_value:.0f}"
                self.totals_label.config(text=totals_text)
            else:
                self.totals_label.config(text="")
                
        except Exception as e:
            logger.error(f"Error calculando totales: {e}")
            self.totals_label.config(text="")

    def _on_search_change(self, event=None) -> None:
        """Maneja cambios en el campo de búsqueda."""
        # Aplicar búsqueda automáticamente después de una pausa
        self.window.after(300, self._apply_search)

    def _apply_search(self) -> None:
        """Aplica la búsqueda/filtro."""
        try:
            search_text = self.search_var.get().strip().lower()
            column_filter = self.column_var.get()
            
            if not search_text:
                # Si no hay búsqueda, mostrar todos los datos
                self.df = self.original_df.copy()
            else:
                # Aplicar filtro
                if column_filter == "Todas" or not column_filter:
                    # Buscar en todas las columnas
                    mask = self.original_df.astype(str).apply(
                        lambda x: x.str.lower().str.contains(search_text, na=False)
                    ).any(axis=1)
                else:
                    # Buscar en columna específica
                    mask = self.original_df[column_filter].astype(str).str.lower().str.contains(search_text, na=False)
                
                self.df = self.original_df[mask].copy()
            
            self._load_data()
            
        except Exception as e:
            logger.error(f"Error aplicando búsqueda: {e}")
            messagebox.showerror("Error", f"Error en búsqueda: {str(e)}")

    def _clear_search(self) -> None:
        """Limpia la búsqueda."""
        self.search_var.set("")
        self.column_var.set("Todas")
        self.df = self.original_df.copy()
        self._load_data()

    def _sort_column(self, column: str) -> None:
        """Ordena la tabla por columna."""
        try:
            # Alternar orden ascendente/descendente
            if not hasattr(self, '_sort_reverse'):
                self._sort_reverse = {}
            
            reverse = self._sort_reverse.get(column, False)
            self._sort_reverse[column] = not reverse
            
            # Ordenar DataFrame
            self.df = self.df.sort_values(by=column, ascending=not reverse)
            self._load_data()
            
        except Exception as e:
            logger.error(f"Error ordenando columna: {e}")

    def _on_click(self, event) -> None:
        """Maneja click simple."""
        item = self.tree.identify_row(event.y)
        if item:
            # Deseleccionar todos y seleccionar el clickeado
            self._deselect_all()
            self.tree.selection_set(item)
            self.selected_rows.add(item)
            self._update_info()

    def _on_ctrl_click(self, event) -> None:
        """Maneja Ctrl+Click para selección múltiple."""
        item = self.tree.identify_row(event.y)
        if item:
            if item in self.selected_rows:
                self.tree.selection_remove(item)
                self.selected_rows.discard(item)
            else:
                self.tree.selection_add(item)
                self.selected_rows.add(item)
            self._update_info()

    def _on_shift_click(self, event) -> None:
        """Maneja Shift+Click para selección de rango."""
        item = self.tree.identify_row(event.y)
        if item and self.selected_rows:
            # Seleccionar rango desde la última selección
            all_items = self.tree.get_children()
            last_selected = list(self.selected_rows)[-1]
            
            start_idx = all_items.index(last_selected)
            end_idx = all_items.index(item)
            
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx
            
            for i in range(start_idx, end_idx + 1):
                self.tree.selection_add(all_items[i])
                self.selected_rows.add(all_items[i])
            
            self._update_info()

    def _on_double_click(self, event) -> None:
        """Maneja doble click para ver detalles."""
        item = self.tree.identify_row(event.y)
        if item:
            self._view_row_details(item)

    def _select_all(self) -> None:
        """Selecciona todas las filas."""
        self.selected_rows.clear()
        for item in self.tree.get_children():
            self.tree.selection_add(item)
            self.selected_rows.add(item)
        self._update_info()

    def _deselect_all(self) -> None:
        """Deselecciona todas las filas."""
        self.tree.selection_remove(self.tree.selection())
        self.selected_rows.clear()
        self._update_info()

    def _delete_selected(self) -> None:
        """Elimina las filas seleccionadas."""
        if not self.selected_rows:
            messagebox.showwarning("Selección", "No hay filas seleccionadas para eliminar")
            return
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar {len(self.selected_rows)} filas seleccionadas?"):
            try:
                # Obtener índices de las filas seleccionadas
                indices_to_remove = []
                for item in self.selected_rows:
                    tags = self.tree.item(item, "tags")
                    if tags:
                        indices_to_remove.append(int(tags[0]))
                
                # Eliminar del DataFrame
                self.df = self.df.drop(indices_to_remove).reset_index(drop=True)
                self.original_df = self.df.copy()
                
                # Recargar datos
                self.selected_rows.clear()
                self._load_data()
                
                messagebox.showinfo("Éxito", f"Se eliminaron {len(indices_to_remove)} filas")
                
            except Exception as e:
                logger.error(f"Error eliminando filas: {e}")
                messagebox.showerror("Error", f"Error al eliminar filas: {str(e)}")

    def _view_row_details(self, item) -> None:
        """Muestra detalles de una fila."""
        try:
            values = self.tree.item(item, "values")
            
            # Crear ventana de detalles
            details_window = tk.Toplevel(self.window)
            details_window.title("Detalles de la Fila")
            details_window.geometry("400x500")
            details_window.transient(self.window)
            
            # Contenido
            details_frame = ttk.Frame(details_window, padding=20)
            details_frame.pack(fill="both", expand=True)
            
            tk.Label(details_frame, text="📄 Detalles de la Fila", font=("Arial", 14, "bold")).pack(pady=(0, 15))
            
            # Crear tabla de detalles
            details_tree = ttk.Treeview(details_frame, columns=("Campo", "Valor"), show="headings", height=15)
            details_tree.heading("Campo", text="Campo")
            details_tree.heading("Valor", text="Valor")
            details_tree.column("Campo", width=150)
            details_tree.column("Valor", width=200)
            
            # Agregar datos
            for i, (col, val) in enumerate(zip(self.columns, values)):
                details_tree.insert("", "end", values=(col, val))
            
            details_tree.pack(fill="both", expand=True)
            
            # Botón cerrar
            ttk.Button(details_frame, text="Cerrar", command=details_window.destroy).pack(pady=(10, 0))
            
        except Exception as e:
            logger.error(f"Error mostrando detalles: {e}")

    def _print_data(self) -> None:
        """Imprime los datos."""
        try:
            # Crear ventana de opciones de impresión
            print_window = tk.Toplevel(self.window)
            print_window.title("Opciones de Impresión")
            print_window.geometry("300x200")
            print_window.transient(self.window)
            
            print_frame = ttk.Frame(print_window, padding=20)
            print_frame.pack(fill="both", expand=True)
            
            tk.Label(print_frame, text="🖨️ Opciones de Impresión", font=("Arial", 12, "bold")).pack(pady=(0, 15))
            
            # Opciones
            print_all_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(print_frame, text="Imprimir todos los datos", variable=print_all_var).pack(anchor="w", pady=5)
            
            print_selected_var = tk.BooleanVar()
            ttk.Checkbutton(print_frame, text="Solo filas seleccionadas", variable=print_selected_var).pack(anchor="w", pady=5)
            
            include_headers_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(print_frame, text="Incluir encabezados", variable=include_headers_var).pack(anchor="w", pady=5)
            
            # Botones
            buttons_frame = ttk.Frame(print_frame)
            buttons_frame.pack(pady=(15, 0))
            
            def do_print():
                messagebox.showinfo("Impresión", "Funcionalidad de impresión en desarrollo")
                print_window.destroy()
            
            ttk.Button(buttons_frame, text="Imprimir", command=do_print).pack(side="left", padx=(0, 10))
            ttk.Button(buttons_frame, text="Cancelar", command=print_window.destroy).pack(side="left")
            
        except Exception as e:
            logger.error(f"Error en impresión: {e}")
            messagebox.showerror("Error", f"Error en impresión: {str(e)}")

    def _close_window(self) -> None:
        """Cierra la ventana."""
        self.window.destroy()

    def get_dataframe(self) -> pd.DataFrame:
        """Retorna el DataFrame actual (después de filtros/eliminaciones)."""
        return self.df.copy()


def show_data_view(parent: tk.Tk, dataframe: pd.DataFrame, title: str = "Vista Previa") -> Optional[pd.DataFrame]:
    """
    Muestra la vista de datos y retorna el DataFrame modificado.
    
    Args:
        parent: Ventana padre
        dataframe: DataFrame a mostrar
        title: Título de la ventana
        
    Returns:
        DataFrame modificado o None si se cancela
    """
    try:
        data_view = DataViewWindow(parent, dataframe, title)
        parent.wait_window(data_view.window)
        return data_view.get_dataframe()
    except Exception as e:
        logger.error(f"Error mostrando vista de datos: {e}")
        messagebox.showerror("Error", f"Error al mostrar datos: {str(e)}")
        return None

