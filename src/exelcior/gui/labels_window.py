"""
Editor de etiquetas Zebra completo.

Implementa el editor de etiquetas con diseño visual y generación de código ZPL.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from typing import Optional, Dict, Any, List
import json
from pathlib import Path

from ..utils import get_logger

logger = get_logger("exelcior.gui.labels_window")


class ZebraLabelEditor:
    """
    Editor visual de etiquetas Zebra con generación de código ZPL.
    
    Permite diseñar etiquetas visualmente y generar el código ZPL correspondiente.
    """

    def __init__(self, parent: tk.Tk):
        """
        Inicializa el editor de etiquetas.
        
        Args:
            parent: Ventana padre
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Editor de Etiquetas Zebra")
        self.window.geometry("900x700")
        self.window.transient(parent)
        
        # Variables del editor
        self.label_width = 400
        self.label_height = 300
        self.elements = []
        self.selected_element = None
        
        self._create_interface()

    def _create_interface(self) -> None:
        """Crea la interfaz del editor."""
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="🏷️ Editor de Etiquetas Zebra",
            font=("Arial", 16, "bold"),
            fg="#2C3E50"
        )
        title_label.pack(pady=(0, 10))
        
        # Frame superior con herramientas
        tools_frame = ttk.Frame(main_frame)
        tools_frame.pack(fill="x", pady=(0, 10))
        
        self._create_toolbar(tools_frame)
        
        # Frame principal dividido
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Panel izquierdo - Propiedades
        self._create_properties_panel(content_frame)
        
        # Panel central - Canvas de diseño
        self._create_design_canvas(content_frame)
        
        # Panel derecho - Código ZPL
        self._create_zpl_panel(content_frame)

    def _create_toolbar(self, parent: ttk.Frame) -> None:
        """Crea la barra de herramientas."""
        # Herramientas de archivo
        file_frame = ttk.LabelFrame(parent, text="Archivo", padding=5)
        file_frame.pack(side="left", padx=(0, 10))
        
        ttk.Button(file_frame, text="📄 Nuevo", command=self._new_label, width=8).pack(side="left", padx=2)
        ttk.Button(file_frame, text="📁 Abrir", command=self._open_label, width=8).pack(side="left", padx=2)
        ttk.Button(file_frame, text="💾 Guardar", command=self._save_label, width=8).pack(side="left", padx=2)
        
        # Herramientas de elementos
        elements_frame = ttk.LabelFrame(parent, text="Elementos", padding=5)
        elements_frame.pack(side="left", padx=(0, 10))
        
        ttk.Button(elements_frame, text="📝 Texto", command=self._add_text, width=8).pack(side="left", padx=2)
        ttk.Button(elements_frame, text="📊 Código", command=self._add_barcode, width=8).pack(side="left", padx=2)
        ttk.Button(elements_frame, text="🖼️ Imagen", command=self._add_image, width=8).pack(side="left", padx=2)
        ttk.Button(elements_frame, text="📦 Caja", command=self._add_box, width=8).pack(side="left", padx=2)
        
        # Herramientas de impresión
        print_frame = ttk.LabelFrame(parent, text="Impresión", padding=5)
        print_frame.pack(side="left", padx=(0, 10))
        
        ttk.Button(print_frame, text="👁️ Vista Previa", command=self._preview_label, width=10).pack(side="left", padx=2)
        ttk.Button(print_frame, text="🖨️ Imprimir", command=self._print_label, width=10).pack(side="left", padx=2)

    def _create_properties_panel(self, parent: ttk.Frame) -> None:
        """Crea el panel de propiedades."""
        props_frame = ttk.LabelFrame(parent, text="Propiedades", padding=10)
        props_frame.pack(side="left", fill="y", padx=(0, 10))
        
        # Propiedades de la etiqueta
        label_props_frame = ttk.LabelFrame(props_frame, text="Etiqueta", padding=5)
        label_props_frame.pack(fill="x", pady=(0, 10))
        
        # Tamaño de etiqueta
        ttk.Label(label_props_frame, text="Ancho:").pack(anchor="w")
        self.width_var = tk.StringVar(value="400")
        width_entry = ttk.Entry(label_props_frame, textvariable=self.width_var, width=10)
        width_entry.pack(fill="x", pady=(0, 5))
        width_entry.bind("<KeyRelease>", self._update_label_size)
        
        ttk.Label(label_props_frame, text="Alto:").pack(anchor="w")
        self.height_var = tk.StringVar(value="300")
        height_entry = ttk.Entry(label_props_frame, textvariable=self.height_var, width=10)
        height_entry.pack(fill="x", pady=(0, 5))
        height_entry.bind("<KeyRelease>", self._update_label_size)
        
        # Propiedades del elemento seleccionado
        self.element_props_frame = ttk.LabelFrame(props_frame, text="Elemento", padding=5)
        self.element_props_frame.pack(fill="x", pady=(0, 10))
        
        # Lista de elementos
        elements_list_frame = ttk.LabelFrame(props_frame, text="Elementos", padding=5)
        elements_list_frame.pack(fill="both", expand=True)
        
        self.elements_listbox = tk.Listbox(elements_list_frame, height=8)
        self.elements_listbox.pack(fill="both", expand=True)
        self.elements_listbox.bind("<<ListboxSelect>>", self._select_element)
        
        # Botones de elementos
        elements_buttons_frame = ttk.Frame(elements_list_frame)
        elements_buttons_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Button(elements_buttons_frame, text="🗑️", command=self._delete_element, width=3).pack(side="left")
        ttk.Button(elements_buttons_frame, text="⬆️", command=self._move_element_up, width=3).pack(side="left", padx=(5, 0))
        ttk.Button(elements_buttons_frame, text="⬇️", command=self._move_element_down, width=3).pack(side="left", padx=(5, 0))

    def _create_design_canvas(self, parent: ttk.Frame) -> None:
        """Crea el canvas de diseño."""
        canvas_frame = ttk.LabelFrame(parent, text="Diseño", padding=10)
        canvas_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Canvas con scrollbars
        canvas_container = ttk.Frame(canvas_frame)
        canvas_container.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(
            canvas_container,
            bg="white",
            width=self.label_width + 50,
            height=self.label_height + 50,
            scrollregion=(0, 0, 500, 400)
        )
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_container, orient="horizontal", command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars y canvas
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Dibujar etiqueta inicial
        self._draw_label_outline()
        
        # Eventos del canvas
        self.canvas.bind("<Button-1>", self._canvas_click)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_release)

    def _create_zpl_panel(self, parent: ttk.Frame) -> None:
        """Crea el panel de código ZPL."""
        zpl_frame = ttk.LabelFrame(parent, text="Código ZPL", padding=10)
        zpl_frame.pack(side="right", fill="y")
        
        # Text widget para código ZPL
        self.zpl_text = tk.Text(
            zpl_frame,
            width=30,
            height=25,
            font=("Courier", 9),
            wrap="none"
        )
        self.zpl_text.pack(fill="both", expand=True)
        
        # Scrollbar para ZPL
        zpl_scrollbar = ttk.Scrollbar(zpl_frame, orient="vertical", command=self.zpl_text.yview)
        zpl_scrollbar.pack(side="right", fill="y")
        self.zpl_text.configure(yscrollcommand=zpl_scrollbar.set)
        
        # Botones ZPL
        zpl_buttons_frame = ttk.Frame(zpl_frame)
        zpl_buttons_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Button(zpl_buttons_frame, text="🔄 Actualizar", command=self._generate_zpl, width=12).pack(fill="x", pady=(0, 2))
        ttk.Button(zpl_buttons_frame, text="📋 Copiar", command=self._copy_zpl, width=12).pack(fill="x", pady=(0, 2))
        ttk.Button(zpl_buttons_frame, text="💾 Exportar", command=self._export_zpl, width=12).pack(fill="x")

    def _draw_label_outline(self) -> None:
        """Dibuja el contorno de la etiqueta."""
        self.canvas.delete("label_outline")
        self.canvas.create_rectangle(
            25, 25, 
            25 + self.label_width, 25 + self.label_height,
            outline="black", width=2, tags="label_outline"
        )

    def _update_label_size(self, event=None) -> None:
        """Actualiza el tamaño de la etiqueta."""
        try:
            self.label_width = int(self.width_var.get())
            self.label_height = int(self.height_var.get())
            self._draw_label_outline()
            self._generate_zpl()
        except ValueError:
            pass

    # Métodos para agregar elementos

    def _add_text(self) -> None:
        """Agrega un elemento de texto."""
        text = tk.simpledialog.askstring("Texto", "Ingrese el texto:")
        if text:
            element = {
                "type": "text",
                "text": text,
                "x": 50,
                "y": 50,
                "font_size": 12,
                "font_family": "Arial",
                "color": "black"
            }
            self.elements.append(element)
            self._update_elements_list()
            self._draw_elements()
            self._generate_zpl()

    def _add_barcode(self) -> None:
        """Agrega un código de barras."""
        code = tk.simpledialog.askstring("Código de Barras", "Ingrese el código:")
        if code:
            element = {
                "type": "barcode",
                "code": code,
                "x": 50,
                "y": 100,
                "width": 100,
                "height": 50,
                "barcode_type": "CODE128"
            }
            self.elements.append(element)
            self._update_elements_list()
            self._draw_elements()
            self._generate_zpl()

    def _add_image(self) -> None:
        """Agrega una imagen."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if file_path:
            element = {
                "type": "image",
                "path": file_path,
                "x": 50,
                "y": 150,
                "width": 80,
                "height": 60
            }
            self.elements.append(element)
            self._update_elements_list()
            self._draw_elements()
            self._generate_zpl()

    def _add_box(self) -> None:
        """Agrega una caja/rectángulo."""
        element = {
            "type": "box",
            "x": 50,
            "y": 200,
            "width": 100,
            "height": 50,
            "line_width": 2,
            "color": "black"
        }
        self.elements.append(element)
        self._update_elements_list()
        self._draw_elements()
        self._generate_zpl()

    def _draw_elements(self) -> None:
        """Dibuja todos los elementos en el canvas."""
        self.canvas.delete("element")
        
        for i, element in enumerate(self.elements):
            x = element["x"] + 25
            y = element["y"] + 25
            
            if element["type"] == "text":
                self.canvas.create_text(
                    x, y,
                    text=element["text"],
                    anchor="nw",
                    font=(element.get("font_family", "Arial"), element.get("font_size", 12)),
                    fill=element.get("color", "black"),
                    tags=("element", f"element_{i}")
                )
            
            elif element["type"] == "barcode":
                # Representar código de barras como rectángulo con texto
                self.canvas.create_rectangle(
                    x, y, x + element["width"], y + element["height"],
                    outline="black", fill="white",
                    tags=("element", f"element_{i}")
                )
                self.canvas.create_text(
                    x + element["width"]//2, y + element["height"]//2,
                    text=f"BC: {element['code']}",
                    font=("Arial", 8),
                    tags=("element", f"element_{i}")
                )
            
            elif element["type"] == "image":
                # Representar imagen como rectángulo
                self.canvas.create_rectangle(
                    x, y, x + element["width"], y + element["height"],
                    outline="blue", fill="lightblue",
                    tags=("element", f"element_{i}")
                )
                self.canvas.create_text(
                    x + element["width"]//2, y + element["height"]//2,
                    text="IMG",
                    font=("Arial", 10),
                    tags=("element", f"element_{i}")
                )
            
            elif element["type"] == "box":
                self.canvas.create_rectangle(
                    x, y, x + element["width"], y + element["height"],
                    outline=element.get("color", "black"),
                    width=element.get("line_width", 2),
                    tags=("element", f"element_{i}")
                )

    def _update_elements_list(self) -> None:
        """Actualiza la lista de elementos."""
        self.elements_listbox.delete(0, tk.END)
        for i, element in enumerate(self.elements):
            if element["type"] == "text":
                text = f"Texto: {element['text'][:20]}"
            elif element["type"] == "barcode":
                text = f"Código: {element['code'][:20]}"
            elif element["type"] == "image":
                text = f"Imagen: {Path(element['path']).name[:20]}"
            elif element["type"] == "box":
                text = f"Caja: {element['width']}x{element['height']}"
            else:
                text = f"Elemento {i+1}"
            
            self.elements_listbox.insert(tk.END, text)

    def _select_element(self, event=None) -> None:
        """Selecciona un elemento de la lista."""
        selection = self.elements_listbox.curselection()
        if selection:
            self.selected_element = selection[0]
            self._show_element_properties()

    def _show_element_properties(self) -> None:
        """Muestra las propiedades del elemento seleccionado."""
        # Limpiar propiedades anteriores
        for widget in self.element_props_frame.winfo_children():
            widget.destroy()
        
        if self.selected_element is None or self.selected_element >= len(self.elements):
            return
        
        element = self.elements[self.selected_element]
        
        # Propiedades comunes
        ttk.Label(self.element_props_frame, text="X:").pack(anchor="w")
        x_var = tk.StringVar(value=str(element["x"]))
        x_entry = ttk.Entry(self.element_props_frame, textvariable=x_var, width=10)
        x_entry.pack(fill="x", pady=(0, 5))
        
        ttk.Label(self.element_props_frame, text="Y:").pack(anchor="w")
        y_var = tk.StringVar(value=str(element["y"]))
        y_entry = ttk.Entry(self.element_props_frame, textvariable=y_var, width=10)
        y_entry.pack(fill="x", pady=(0, 5))
        
        # Propiedades específicas según tipo
        if element["type"] == "text":
            ttk.Label(self.element_props_frame, text="Texto:").pack(anchor="w")
            text_var = tk.StringVar(value=element["text"])
            text_entry = ttk.Entry(self.element_props_frame, textvariable=text_var, width=15)
            text_entry.pack(fill="x", pady=(0, 5))
            
            ttk.Label(self.element_props_frame, text="Tamaño:").pack(anchor="w")
            size_var = tk.StringVar(value=str(element.get("font_size", 12)))
            size_entry = ttk.Entry(self.element_props_frame, textvariable=size_var, width=10)
            size_entry.pack(fill="x", pady=(0, 5))
        
        # Botón actualizar
        ttk.Button(
            self.element_props_frame,
            text="Actualizar",
            command=lambda: self._update_element_properties(x_var, y_var, locals())
        ).pack(pady=(10, 0))

    def _update_element_properties(self, x_var, y_var, local_vars) -> None:
        """Actualiza las propiedades del elemento."""
        if self.selected_element is None:
            return
        
        try:
            element = self.elements[self.selected_element]
            element["x"] = int(x_var.get())
            element["y"] = int(y_var.get())
            
            # Actualizar propiedades específicas
            if element["type"] == "text" and "text_var" in local_vars:
                element["text"] = local_vars["text_var"].get()
                element["font_size"] = int(local_vars["size_var"].get())
            
            self._draw_elements()
            self._generate_zpl()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Valores inválidos: {str(e)}")

    def _generate_zpl(self) -> None:
        """Genera el código ZPL."""
        zpl_code = "^XA\n"  # Inicio de etiqueta
        
        # Configuración de etiqueta
        zpl_code += f"^PW{self.label_width}\n"  # Ancho de etiqueta
        zpl_code += f"^LL{self.label_height}\n"  # Largo de etiqueta
        
        # Elementos
        for element in self.elements:
            if element["type"] == "text":
                zpl_code += f"^FO{element['x']},{element['y']}\n"
                zpl_code += f"^A0N,{element.get('font_size', 12)},{element.get('font_size', 12)}\n"
                zpl_code += f"^FD{element['text']}^FS\n"
            
            elif element["type"] == "barcode":
                zpl_code += f"^FO{element['x']},{element['y']}\n"
                zpl_code += f"^BY2,3,{element['height']}\n"
                zpl_code += f"^BC^FD{element['code']}^FS\n"
            
            elif element["type"] == "box":
                zpl_code += f"^FO{element['x']},{element['y']}\n"
                zpl_code += f"^GB{element['width']},{element['height']},{element.get('line_width', 2)}^FS\n"
        
        zpl_code += "^XZ\n"  # Fin de etiqueta
        
        # Actualizar texto ZPL
        self.zpl_text.delete(1.0, tk.END)
        self.zpl_text.insert(1.0, zpl_code)

    # Métodos de eventos del canvas

    def _canvas_click(self, event) -> None:
        """Maneja click en el canvas."""
        pass

    def _canvas_drag(self, event) -> None:
        """Maneja arrastre en el canvas."""
        pass

    def _canvas_release(self, event) -> None:
        """Maneja liberación del mouse en el canvas."""
        pass

    # Métodos de archivo

    def _new_label(self) -> None:
        """Crea una nueva etiqueta."""
        if messagebox.askyesno("Nueva Etiqueta", "¿Crear nueva etiqueta? Se perderán los cambios no guardados."):
            self.elements.clear()
            self._update_elements_list()
            self._draw_elements()
            self._generate_zpl()

    def _open_label(self) -> None:
        """Abre una etiqueta guardada."""
        file_path = filedialog.askopenfilename(
            title="Abrir etiqueta",
            filetypes=[("Archivos de etiqueta", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.elements = data.get("elements", [])
                self.label_width = data.get("width", 400)
                self.label_height = data.get("height", 300)
                
                self.width_var.set(str(self.label_width))
                self.height_var.set(str(self.label_height))
                
                self._draw_label_outline()
                self._update_elements_list()
                self._draw_elements()
                self._generate_zpl()
                
                messagebox.showinfo("Éxito", "Etiqueta cargada correctamente")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al abrir etiqueta: {str(e)}")

    def _save_label(self) -> None:
        """Guarda la etiqueta actual."""
        file_path = filedialog.asksaveasfilename(
            title="Guardar etiqueta",
            defaultextension=".json",
            filetypes=[("Archivos de etiqueta", "*.json")]
        )
        if file_path:
            try:
                data = {
                    "width": self.label_width,
                    "height": self.label_height,
                    "elements": self.elements
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Éxito", "Etiqueta guardada correctamente")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar etiqueta: {str(e)}")

    # Métodos de elementos

    def _delete_element(self) -> None:
        """Elimina el elemento seleccionado."""
        if self.selected_element is not None:
            del self.elements[self.selected_element]
            self.selected_element = None
            self._update_elements_list()
            self._draw_elements()
            self._generate_zpl()

    def _move_element_up(self) -> None:
        """Mueve el elemento hacia arriba en la lista."""
        if self.selected_element is not None and self.selected_element > 0:
            self.elements[self.selected_element], self.elements[self.selected_element - 1] = \
                self.elements[self.selected_element - 1], self.elements[self.selected_element]
            self.selected_element -= 1
            self._update_elements_list()
            self.elements_listbox.selection_set(self.selected_element)
            self._draw_elements()

    def _move_element_down(self) -> None:
        """Mueve el elemento hacia abajo en la lista."""
        if self.selected_element is not None and self.selected_element < len(self.elements) - 1:
            self.elements[self.selected_element], self.elements[self.selected_element + 1] = \
                self.elements[self.selected_element + 1], self.elements[self.selected_element]
            self.selected_element += 1
            self._update_elements_list()
            self.elements_listbox.selection_set(self.selected_element)
            self._draw_elements()

    # Métodos ZPL

    def _copy_zpl(self) -> None:
        """Copia el código ZPL al portapapeles."""
        zpl_code = self.zpl_text.get(1.0, tk.END)
        self.window.clipboard_clear()
        self.window.clipboard_append(zpl_code)
        messagebox.showinfo("Copiado", "Código ZPL copiado al portapapeles")

    def _export_zpl(self) -> None:
        """Exporta el código ZPL a un archivo."""
        file_path = filedialog.asksaveasfilename(
            title="Exportar código ZPL",
            defaultextension=".zpl",
            filetypes=[("Archivos ZPL", "*.zpl"), ("Archivos de texto", "*.txt")]
        )
        if file_path:
            try:
                zpl_code = self.zpl_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(zpl_code)
                messagebox.showinfo("Éxito", "Código ZPL exportado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al exportar: {str(e)}")

    # Métodos de impresión

    def _preview_label(self) -> None:
        """Muestra vista previa de la etiqueta."""
        messagebox.showinfo("Vista Previa", "Vista previa en desarrollo")

    def _print_label(self) -> None:
        """Imprime la etiqueta."""
        messagebox.showinfo("Imprimir", "Impresión directa en desarrollo")


def open_labels_window(parent: tk.Tk) -> None:
    """
    Abre el editor de etiquetas Zebra.
    
    Args:
        parent: Ventana padre
    """
    try:
        ZebraLabelEditor(parent)
    except Exception as e:
        logger.error(f"Error abriendo editor de etiquetas: {e}")
        messagebox.showerror("Error", f"Error al abrir editor: {str(e)}")

