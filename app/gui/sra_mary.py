# Módulo: sra_mary.py
# Descripción: Gestión de clientes y días de despacho preferidos para FedEx y Urbano

import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Ruta a la base de datos JSON
DB_PATH = Path("data/sra_mary_db.json")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if not DB_PATH.exists():
    DB_PATH.write_text("[]", encoding="utf-8")

# Logger
logger = logging.getLogger("eventos_logger")

def guardar_datos_json(data: list) -> None:
    """Guarda los datos en formato JSON."""
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("Base de datos actualizada exitosamente.")
    except Exception as e:
        logger.error(f"No se pudo guardar el archivo: {e}")
        raise

def cargar_clientes() -> list:
    """Carga los datos desde el archivo JSON."""
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"No se pudo cargar el archivo: {e}")
        return []

class SraMaryView(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sra Mary - Gestión de Despachos")
        self.geometry("1000x620")
        self.configure(bg="#F3F4F6")

        self.dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        self.vars_fedex = {dia: tk.BooleanVar() for dia in self.dias_semana}
        self.vars_urbano = {dia: tk.BooleanVar() for dia in self.dias_semana}
        self.datos = cargar_clientes()
        self.index_edicion = None

        self._crear_widgets()
        self._cargar_datos_en_tree()

    def _crear_widgets(self):
        """Inicializa y organiza todos los elementos de la UI."""
        frame_sup = tk.Frame(self, bg="#F3F4F6")
        frame_sup.pack(pady=5)

        tk.Label(frame_sup, text="Cliente:", bg="#F3F4F6").grid(row=0, column=0, padx=5)
        self.entry_cliente = tk.Entry(frame_sup, width=30)
        self.entry_cliente.grid(row=0, column=1, padx=5)

        tk.Label(frame_sup, text="Buscar Cliente:", bg="#F3F4F6").grid(row=0, column=2, padx=5)
        self.entry_busqueda = tk.Entry(frame_sup, width=30)
        self.entry_busqueda.grid(row=0, column=3, padx=5)
        self.entry_busqueda.bind("<KeyRelease>", lambda e: self._filtrar_tree())

        frame_chk = tk.Frame(self, bg="#F3F4F6")
        frame_chk.pack(pady=10)

        # Checkboxes FedEx
        frame_fedex = tk.LabelFrame(frame_chk, text="FedEx", bg="#F3F4F6", font=("Segoe UI", 10, "bold"))
        frame_fedex.grid(row=0, column=0, padx=30)
        for i, dia in enumerate(self.dias_semana):
            ttk.Checkbutton(frame_fedex, text=dia, variable=self.vars_fedex[dia]).grid(row=i, sticky="w")

        # Checkboxes Urbano
        frame_urbano = tk.LabelFrame(frame_chk, text="Urbano", bg="#F3F4F6", font=("Segoe UI", 10, "bold"))
        frame_urbano.grid(row=0, column=1, padx=30)
        for i, dia in enumerate(self.dias_semana):
            ttk.Checkbutton(frame_urbano, text=dia, variable=self.vars_urbano[dia]).grid(row=i, sticky="w")

        # Botones
        frame_btns = tk.Frame(self, bg="#F3F4F6")
        frame_btns.pack(pady=5)
        ttk.Button(frame_btns, text="Guardar Cliente", command=self._guardar).grid(row=0, column=0, padx=5)
        ttk.Button(frame_btns, text="Actualizar Selección", command=self._actualizar).grid(row=0, column=1, padx=5)
        ttk.Button(frame_btns, text="Eliminar Selección", command=self._eliminar).grid(row=0, column=2, padx=5)

        # Tabla
        self.tree = ttk.Treeview(self, columns=("Cliente", "FedEx", "Urbano"), show="headings", height=10)
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=300, anchor="center")
        self.tree.pack(padx=10, pady=10)
        self.tree.bind("<Double-1>", self._cargar_edicion)

    def _guardar(self):
        """Guarda un nuevo cliente en la base de datos."""
        cliente = self.entry_cliente.get().strip()
        if not cliente:
            return messagebox.showwarning("Falta Cliente", "Ingrese el nombre del cliente.")

        if any(c["cliente"].lower() == cliente.lower() for c in self.datos):
            return messagebox.showerror("Duplicado", f"El cliente '{cliente}' ya está registrado.")

        dias_fedex = [d for d, v in self.vars_fedex.items() if v.get()]
        dias_urbano = [d for d, v in self.vars_urbano.items() if v.get()]
        if not dias_fedex and not dias_urbano:
            return messagebox.showwarning("Sin Días", "Seleccione al menos un día de despacho.")

        nuevo = {
            "cliente": cliente,
            "fedex_dias": dias_fedex,
            "urbano_dias": dias_urbano
        }

        self.datos.append(nuevo)
        guardar_datos_json(self.datos)
        self._limpiar_formulario()
        self._cargar_datos_en_tree()
        logger.info(f"Cliente agregado: {cliente}")

    def _cargar_datos_en_tree(self):
        """Carga los clientes en la tabla (Treeview)."""
        self.tree.delete(*self.tree.get_children())
        for item in self.datos:
            self.tree.insert("", "end", values=(item["cliente"], ", ".join(item["fedex_dias"]), ", ".join(item["urbano_dias"])))

    def _filtrar_tree(self):
        """Filtra la tabla según el término buscado."""
        termino = self.entry_busqueda.get().lower()
        self.tree.delete(*self.tree.get_children())
        for item in self.datos:
            if termino in item["cliente"].lower():
                self.tree.insert("", "end", values=(item["cliente"], ", ".join(item["fedex_dias"]), ", ".join(item["urbano_dias"])))

    def _cargar_edicion(self, event):
        """Carga los datos del cliente seleccionado en el formulario."""
        seleccion = self.tree.focus()
        if not seleccion:
            return
        index = self.tree.index(seleccion)
        cliente = self.datos[index]
        self.index_edicion = index

        self.entry_cliente.delete(0, tk.END)
        self.entry_cliente.insert(0, cliente["cliente"])
        for dia in self.dias_semana:
            self.vars_fedex[dia].set(dia in cliente["fedex_dias"])
            self.vars_urbano[dia].set(dia in cliente["urbano_dias"])

    def _actualizar(self):
        """Actualiza un cliente existente."""
        if self.index_edicion is None:
            return messagebox.showwarning("Sin selección", "Debes seleccionar un cliente desde la lista.")

        cliente = self.entry_cliente.get().strip()
        if not cliente:
            return messagebox.showwarning("Falta Cliente", "Ingrese el nombre del cliente.")

        for i, c in enumerate(self.datos):
            if i != self.index_edicion and c["cliente"].lower() == cliente.lower():
                return messagebox.showerror("Duplicado", f"Ya existe un cliente con el nombre '{cliente}'.")

        dias_fedex = [d for d, v in self.vars_fedex.items() if v.get()]
        dias_urbano = [d for d, v in self.vars_urbano.items() if v.get()]

        self.datos[self.index_edicion] = {
            "cliente": cliente,
            "fedex_dias": dias_fedex,
            "urbano_dias": dias_urbano
        }

        guardar_datos_json(self.datos)
        self._limpiar_formulario()
        self._cargar_datos_en_tree()
        logger.info(f"Cliente actualizado: {cliente}")

    def _eliminar(self):
        """Elimina el cliente seleccionado."""
        seleccion = self.tree.focus()
        if not seleccion:
            return messagebox.showwarning("Sin selección", "Debes seleccionar un cliente para eliminar.")

        index = self.tree.index(seleccion)
        cliente = self.datos[index]["cliente"]

        if messagebox.askyesno("Confirmar", f"¿Eliminar al cliente '{cliente}'?"):
            self.datos.pop(index)
            guardar_datos_json(self.datos)
            self._cargar_datos_en_tree()
            self._limpiar_formulario()
            logger.info(f"Cliente eliminado: {cliente}")

    def _limpiar_formulario(self):
        """Limpia los campos del formulario."""
        self.entry_cliente.delete(0, tk.END)
        for v in self.vars_fedex.values():
            v.set(False)
        for v in self.vars_urbano.values():
            v.set(False)
        self.index_edicion = None
