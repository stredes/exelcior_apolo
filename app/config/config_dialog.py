import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path
from typing import List, Set, Dict
from app.db.utils_db import CONFIG_FILE, save_config

DEFAULT_CONFIG = {
    "fedex": {
        "eliminar": [
            "errors", "senderAccountNumber", "poNumber", "senderLine1", "senderPostcode", "totalShipmentWeight",
            "weightUnits", "recipientPostcode", "creationDate", "recipientPhoneExtension", "senderContactNumber",
            "senderCity", "length", "senderEmail", "senderLine2", "recipientState", "packageWeight",
            "returnRmaNumber", "invoiceNumber", "paymentType", "senderContactName", "recipientContactNumber",
            "departmentNumber", "senderState", "status", "recipientTin", "estimatedShippingCosts",
            "recipientEmail", "senderCompany", "recipientResidential", "senderPhoneExtension", "senderTin",
            "height", "returnReason", "width", "etdEnabled", "quoteId", "recipientLine2", "recipientCountry",
            "senderResidential", "recipientLine1", "pickupId", "returnTrackingId", "senderLine3", "shipmentType",
            "senderCountry"
        ],
        "sumar": ["numberOfPackages"],
        "mantener_formato": ["masterTrackingNumber"],
        "start_row": 0,
        "nombre_archivo_digitos": [],
        "vista_previa_fuente": 10
    },
    "urbano": {
        "eliminar": ["AGENCIA", "SHIPPER", "FECHA CHK", "DIAS", "ESTADO", "SERVICIO", "PESO"],
        "sumar": ["PIEZAS"],
        "mantener_formato": [],
        "start_row": 2,
        "nombre_archivo_digitos": [9, 10],
        "vista_previa_fuente": 10
    },
    "listados": {
        "eliminar": ["Moneda", "Fecha doc.", "RUT", "Vendedor", "Glosa", "Total", "Tipo cambio"],
        "sumar": [],
        "mantener_formato": [],
        "start_row": 0,
        "nombre_archivo_digitos": [],
        "vista_previa_fuente": 10
    }
}

class ConfigDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, mode: str, available_columns: List[str], config_columns: Dict[str, Dict[str, Set[str]]]) -> None:
        super().__init__(parent)
        self.title(f"Configuración - {mode.capitalize()}")
        self.geometry("1000x900")
        self.configure(background="#ffffff")

        self.mode: str = mode
        self.available_columns: List[str] = available_columns
        self.config_columns = config_columns

        self.selected_eliminar: Set[str] = set()
        self.selected_sumar: Set[str] = set()
        self.selected_preservar: Set[str] = set()
        self.start_row: tk.IntVar = tk.IntVar(value=self.config_columns.get(mode, {}).get("start_row", 0))
        self.nombre_archivo_digitos: tk.StringVar = tk.StringVar(value=",".join(map(str, self.config_columns.get(mode, {}).get("nombre_archivo_digitos", []))))
        self.preview_font_size: tk.IntVar = tk.IntVar(value=self.config_columns.get(mode, {}).get("vista_previa_fuente", 10))

        self._create_widgets()
        self._load_initial_selection()

    def _create_widgets(self) -> None:
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        frame_elim = ttk.LabelFrame(container, text="Columnas a eliminar", padding=10)
        frame_elim.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.listbox_eliminar = tk.Listbox(frame_elim, selectmode="extended", font=("Helvetica", 10), exportselection=False)
        self.listbox_eliminar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_eliminar.insert(tk.END, col)

        frame_sumar = ttk.LabelFrame(container, text="Columnas para sumatorias", padding=10)
        frame_sumar.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        lbl_info = tk.Label(frame_sumar, text="Las celdas se convertirán a numérico para sumar", bg="#ffffff", font=("Helvetica", 9, "italic"))
        lbl_info.pack(pady=5)
        self.listbox_sumar = tk.Listbox(frame_sumar, selectmode="extended", font=("Helvetica", 10), exportselection=False)
        self.listbox_sumar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_sumar.insert(tk.END, col)

        frame_preservar = ttk.LabelFrame(container, text="Columnas a preservar (sin modificar formato)", padding=10)
        frame_preservar.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.listbox_preservar = tk.Listbox(frame_preservar, selectmode="extended", font=("Helvetica", 10), exportselection=False)
        self.listbox_preservar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_preservar.insert(tk.END, col)

        frame_row = ttk.LabelFrame(container, text="Fila de inicio de datos (start_row)", padding=10)
        frame_row.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.spinbox_row = ttk.Spinbox(frame_row, from_=0, to=20, textvariable=self.start_row, width=5)
        self.spinbox_row.pack(pady=5)

        if self.mode == "urbano":
            frame_digitos = ttk.LabelFrame(container, text="Dígitos del nombre del archivo (urbano)", padding=10)
            frame_digitos.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
            self.entry_digitos = ttk.Entry(frame_digitos, textvariable=self.nombre_archivo_digitos, width=15)
            self.entry_digitos.pack(pady=5)

        if self.mode in ("fedex", "urbano", "listados"):
            frame_fuente = ttk.LabelFrame(container, text="Tamaño de fuente de vista previa", padding=10)
            frame_fuente.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
            self.spin_font = ttk.Spinbox(frame_fuente, from_=8, to=24, textvariable=self.preview_font_size, width=5)
            self.spin_font.pack(pady=5)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        for i in range(4):
            container.rowconfigure(i, weight=0)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Restablecer por defecto", command=self._reset_to_default).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Guardar", command=self._on_save).pack(side=tk.LEFT, padx=5)

    def _load_initial_selection(self) -> None:
        conf = self.config_columns.get(self.mode, {})
        eliminar = conf.get("eliminar", set())
        sumar = conf.get("sumar", set())
        preservar = conf.get("mantener_formato", set())
        for idx, col in enumerate(self.available_columns):
            if col in eliminar:
                self.listbox_eliminar.select_set(idx)
            if self.listbox_sumar and col in sumar:
                self.listbox_sumar.select_set(idx)
            if col in preservar:
                self.listbox_preservar.select_set(idx)

    def _on_save(self) -> None:
        self.selected_eliminar = {self.available_columns[i] for i in self.listbox_eliminar.curselection()}
        self.selected_sumar = {self.available_columns[i] for i in self.listbox_sumar.curselection()} if self.listbox_sumar else set()
        self.selected_preservar = {self.available_columns[i] for i in self.listbox_preservar.curselection()}

        try:
            nombre_digitos = [int(x.strip()) for x in self.nombre_archivo_digitos.get().split(",") if x.strip().isdigit()] if self.mode == "urbano" else []
        except Exception:
            nombre_digitos = [9, 10] if self.mode == "urbano" else []

        self.config_columns[self.mode] = {
            "eliminar": list(self.selected_eliminar),
            "sumar": list(self.selected_sumar),
            "mantener_formato": list(self.selected_preservar),
            "start_row": self.start_row.get(),
            "nombre_archivo_digitos": nombre_digitos,
            "vista_previa_fuente": self.preview_font_size.get()
        }
        save_config(self.config_columns)
        self.destroy()

    def _reset_to_default(self):
        if self.mode in DEFAULT_CONFIG:
            self.config_columns[self.mode] = DEFAULT_CONFIG[self.mode]
            save_config(self.config_columns)
            self.start_row.set(DEFAULT_CONFIG[self.mode].get("start_row", 0))
            if self.mode == "urbano":
                self.nombre_archivo_digitos.set(",".join(map(str, DEFAULT_CONFIG[self.mode].get("nombre_archivo_digitos", []))))
            self.preview_font_size.set(DEFAULT_CONFIG[self.mode].get("vista_previa_fuente", 10))
            self._load_initial_selection()
