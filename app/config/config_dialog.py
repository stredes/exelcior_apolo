# app/config/config_dialog.py

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any

from app.config.config_manager import (
    save_config,
    load_config,
    get_effective_mode_rules,
)
from app.core.logger_eventos import log_evento


class ConfigDialog(tk.Toplevel):
    """
    Dialogo de configuración por modo.
    - Permite definir: columnas a eliminar, sumar, mantener como texto y fila inicial (start_row).
    - Se alimenta y guarda contra la misma fuente de verdad usada por el pipeline:
      app.config.config_manager (load_config / save_config / get_effective_mode_rules).
    """

    def __init__(
        self,
        parent: tk.Tk,
        mode: str,
        available_columns: List[str],
        config_columns: Dict[str, Any],
    ) -> None:
        """
        :param parent: Ventana padre
        :param mode: Modo (p.ej. "listados", "fedex", "urbano")
        :param available_columns: Columnas detectadas en el DataFrame cargado
        :param config_columns: Config actual cargada (se actualizará en memoria y se persistirá)
        """
        super().__init__(parent)
        self.title(f"Configuración - {mode.capitalize()}")
        self.geometry("700x560")
        self.configure(background="#ffffff")
        self.resizable(True, True)

        self.mode = (mode or "").strip().lower()
        self.available_columns = list(available_columns)
        self.config_columns = config_columns if isinstance(config_columns, dict) else {}

        # Estados internos (listas para JSON-friendly)
        self.selected_eliminar: List[str] = []
        self.selected_sumar: List[str] = []
        self.selected_preservar: List[str] = []
        self.selected_formato_texto: List[str] = []
        self.start_row_var = tk.IntVar(value=0)

        self._create_widgets()
        self._load_initial_selection()

        # Centrar sobre el padre
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    # ------------------------------------------------------------------ UI

    def _create_widgets(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # --- Fila inicial (start_row) ---
        frm_top = ttk.LabelFrame(container, text="Fila de inicio (omitidas al leer)", padding=10)
        frm_top.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)

        ttk.Label(frm_top, text="start_row:").grid(row=0, column=0, sticky="w")
        self.spn_start_row = ttk.Spinbox(frm_top, from_=0, to=10000, width=8, textvariable=self.start_row_var)
        self.spn_start_row.grid(row=0, column=1, sticky="w", padx=6)

        # --- Columnas a eliminar ---
        frame_elim = ttk.LabelFrame(container, text="Columnas a eliminar", padding=10)
        frame_elim.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.listbox_eliminar = tk.Listbox(
            frame_elim, selectmode="extended", font=("Segoe UI", 10), exportselection=False
        )
        self.listbox_eliminar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_eliminar.insert(tk.END, col)

        # --- Columnas para sumatorias (visible para modos logísticos comunes) ---
        frame_sumar = ttk.LabelFrame(container, text="Columnas para sumatorias", padding=10)
        frame_sumar.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        lbl_info = tk.Label(
            frame_sumar,
            text="(Se convertirán a numérico antes de sumar)",
            bg="#ffffff",
            font=("Segoe UI", 9, "italic"),
        )
        lbl_info.pack(pady=4)
        self.listbox_sumar = tk.Listbox(
            frame_sumar, selectmode="extended", font=("Segoe UI", 10), exportselection=False
        )
        self.listbox_sumar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_sumar.insert(tk.END, col)

        # --- Preservar formato original (por ahora, se comprende como mantener texto) ---
        frame_preservar = ttk.LabelFrame(container, text="Preservar como texto", padding=10)
        frame_preservar.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)
        self.listbox_preservar = tk.Listbox(
            frame_preservar, selectmode="extended", font=("Segoe UI", 10), exportselection=False
        )
        self.listbox_preservar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_preservar.insert(tk.END, col)

        # --- Formato texto en impresión (si quieres una lista separada para impresión) ---
        frame_texto = ttk.LabelFrame(container, text="Formato texto (solo impresión)", padding=10)
        frame_texto.grid(row=2, column=1, sticky="nsew", padx=6, pady=6)
        self.listbox_formato_texto = tk.Listbox(
            frame_texto, selectmode="extended", font=("Segoe UI", 10), exportselection=False
        )
        self.listbox_formato_texto.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_formato_texto.insert(tk.END, col)

        # Layout flexible
        for r in range(3):
            container.rowconfigure(r, weight=1)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # Botones
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Guardar", command=self._on_save).pack(side=tk.LEFT, padx=6)

    # ------------------------------------------------------------------ Carga inicial

    def _load_initial_selection(self) -> None:
        """
        Carga la selección inicial desde las reglas efectivas del modo (misma fuente que usa el pipeline).
        Si hay diferencias con self.config_columns, prevalece lo efectivo y se sincroniza al guardar.
        """
        # Cargar configuración efectiva de disco (merge default+user/env) para evitar desalineaciones.
        cfg = load_config()
        rules = get_effective_mode_rules(self.mode, cfg)

        eliminar = list(rules.get("eliminar", []))
        sumar = list(rules.get("sumar", []))
        preservar = list(rules.get("mantener_formato", []))
        # Campo opcional para impresión (si no existe, queda vacío)
        formato_texto = list((cfg.get(self.mode, {}) or {}).get("formato_texto", []))
        start_row = int(rules.get("start_row", 0) or 0)

        self.start_row_var.set(start_row)

        # Selecciones en listboxes
        for idx, col in enumerate(self.available_columns):
            if col in eliminar:
                self.listbox_eliminar.select_set(idx)
            if col in sumar:
                self.listbox_sumar.select_set(idx)
            if col in preservar:
                self.listbox_preservar.select_set(idx)
            if col in formato_texto:
                self.listbox_formato_texto.select_set(idx)

        log_evento(
            f"[CONFIG-UI] Inicial para '{self.mode}': start_row={start_row}, "
            f"eliminar={eliminar}, sumar={sumar}, mantener_formato={preservar}, formato_texto={formato_texto}",
            "info",
        )

    # ------------------------------------------------------------------ Guardado

    def _on_save(self) -> None:
        # Lee selecciones desde los listboxes (listas -> JSON friendly)
        self.selected_eliminar = [self.available_columns[i] for i in self.listbox_eliminar.curselection()]
        self.selected_sumar = [self.available_columns[i] for i in self.listbox_sumar.curselection()]
        self.selected_preservar = [self.available_columns[i] for i in self.listbox_preservar.curselection()]
        self.selected_formato_texto = [self.available_columns[i] for i in self.listbox_formato_texto.curselection()]

        # Sincroniza en memoria la estructura self.config_columns (para la sesión)
        # Mantén cualquier otra clave ajena a este modo.
        actual_mode_cfg: Dict[str, Any] = dict(self.config_columns.get(self.mode, {}))
        actual_mode_cfg.update({
            "start_row": int(self.start_row_var.get() or 0),
            "eliminar": self.selected_eliminar,
            "sumar": self.selected_sumar,
            "mantener_formato": self.selected_preservar,
            # Campo opcional que puedes usar en impresión si quieres reglas distintas a mantener_formato
            "formato_texto": self.selected_formato_texto,
        })
        self.config_columns[self.mode] = actual_mode_cfg

        # Cargamos el config global actual desde disco y fusionamos el modo para persistir bien
        cfg_disk = load_config()
        cfg_disk[self.mode] = actual_mode_cfg

        ok = save_config(cfg_disk)
        if ok:
            log_evento(f"[CONFIG-UI] Guardado para '{self.mode}': {actual_mode_cfg}", "info")
        else:
            log_evento(f"[CONFIG-UI] Error al guardar configuración para '{self.mode}'", "error")

        self.destroy()
