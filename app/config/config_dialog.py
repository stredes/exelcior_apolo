import tkinter as tk
from tkinter import ttk
from typing import List, Set, Dict
from app.utils.utils import save_config  # ← Importa desde el nuevo módulo correcto

class ConfigDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, mode: str, available_columns: List[str], config_columns: Dict[str, Dict[str, Set[str]]]) -> None:
        super().__init__(parent)
        self.title(f"Configuración - {mode.capitalize()}")
        self.geometry("600x500")
        self.configure(background="#ffffff")
        self.mode = mode
        self.available_columns = available_columns
        self.config_columns = config_columns

        self.selected_eliminar: Set[str] = set()
        self.selected_sumar: Set[str] = set()
        self.selected_preservar: Set[str] = set()
        self.selected_formato_texto: Set[str] = set()

        self._create_widgets()
        self._load_initial_selection()

    def _create_widgets(self) -> None:
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # Columnas a eliminar
        frame_elim = ttk.LabelFrame(container, text="Columnas a eliminar", padding=10)
        frame_elim.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.listbox_eliminar = tk.Listbox(frame_elim, selectmode="extended", font=("Helvetica", 10), exportselection=False)
        self.listbox_eliminar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_eliminar.insert(tk.END, col)

        # Columnas para sumar (solo en ciertos modos)
        if self.mode in ("urbano", "fedex", "listados"):
            frame_sumar = ttk.LabelFrame(container, text="Columnas para sumatorias", padding=10)
            frame_sumar.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            lbl_info = tk.Label(frame_sumar, text="Convertidas a numérico para sumar", bg="#ffffff", font=("Helvetica", 9, "italic"))
            lbl_info.pack(pady=5)
            self.listbox_sumar = tk.Listbox(frame_sumar, selectmode="extended", font=("Helvetica", 10), exportselection=False)
            self.listbox_sumar.pack(fill="both", expand=True)
            for col in self.available_columns:
                self.listbox_sumar.insert(tk.END, col)
        else:
            self.listbox_sumar = None

        # Columnas a preservar formato
        frame_preservar = ttk.LabelFrame(container, text="Preservar formato original", padding=10)
        frame_preservar.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.listbox_preservar = tk.Listbox(frame_preservar, selectmode="extended", font=("Helvetica", 10), exportselection=False)
        self.listbox_preservar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_preservar.insert(tk.END, col)

        # Columnas como texto en impresión
        frame_texto = ttk.LabelFrame(container, text="Formato texto en impresión", padding=10)
        frame_texto.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.listbox_formato_texto = tk.Listbox(frame_texto, selectmode="extended", font=("Helvetica", 10), exportselection=False)
        self.listbox_formato_texto.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_formato_texto.insert(tk.END, col)

        # Layout flexible
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        # Botones de acción
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Guardar", command=self._on_save).pack(side=tk.LEFT, padx=5)

    def _load_initial_selection(self) -> None:
        conf = self.config_columns.get(self.mode, {})
        eliminar = conf.get("eliminar", set())
        sumar = conf.get("sumar", set())
        preservar = conf.get("mantener_formato", set())
        formato_texto = conf.get("formato_texto", set())

        for idx, col in enumerate(self.available_columns):
            if col in eliminar:
                self.listbox_eliminar.select_set(idx)
            if self.listbox_sumar and col in sumar:
                self.listbox_sumar.select_set(idx)
            if col in preservar:
                self.listbox_preservar.select_set(idx)
            if col in formato_texto:
                self.listbox_formato_texto.select_set(idx)

    def _on_save(self) -> None:
        self.selected_eliminar = {self.available_columns[i] for i in self.listbox_eliminar.curselection()}
        if self.listbox_sumar:
            self.selected_sumar = {self.available_columns[i] for i in self.listbox_sumar.curselection()}
        self.selected_preservar = {self.available_columns[i] for i in self.listbox_preservar.curselection()}
        self.selected_formato_texto = {self.available_columns[i] for i in self.listbox_formato_texto.curselection()}

        self.config_columns[self.mode] = {
            "eliminar": self.selected_eliminar,
            "sumar": self.selected_sumar,
            "mantener_formato": self.selected_preservar,
            "formato_texto": self.selected_formato_texto
        }

        save_config(self.config_columns)
        self.destroy()
