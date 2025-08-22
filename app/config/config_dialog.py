# app/config/config_dialog.py
from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any

from app.config.config_manager import (
    save_config,
    load_config,
    get_effective_mode_rules,
    DEFAULT_CFG_PATH,   # ruta absoluta al default del paquete
)
from app.core.logger_eventos import log_evento


class ConfigDialog(tk.Toplevel):
    """
    Diálogo de configuración por modo (compatible con esquema v2):
      config = {
        "version": 2,
        "paths": {...},
        "modes": {
          "<mode>": {
            "eliminar": [...],
            "sumar": [...],
            "mantener_formato": [...],
            "formato_texto": [...],
            "start_row": int,
            "vista_previa_fuente": int
          }
        }
      }

    Fuente de verdad: config_manager (load_config / save_config / get_effective_mode_rules).
    Botones: Guardar / Cargar por defecto (solo este modo) / Limpiar modo.
    """

    def __init__(
        self,
        parent: tk.Tk,
        mode: str,
        available_columns: List[str],
        config_columns: Dict[str, Any],
    ) -> None:
        super().__init__(parent)
        self.title(f"Configuración - {mode.capitalize()}")
        self.geometry("780x620")
        self.configure(background="#ffffff")
        self.resizable(True, True)

        self.mode = (mode or "").strip().lower()
        self.available_columns = list(available_columns)
        self.config_columns = config_columns if isinstance(config_columns, dict) else {}

        # Estados internos (listas para JSON-friendly)
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

        # --- Columnas para sumatorias ---
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

        # --- Preservar como texto ---
        frame_preservar = ttk.LabelFrame(container, text="Preservar como texto", padding=10)
        frame_preservar.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)
        self.listbox_preservar = tk.Listbox(
            frame_preservar, selectmode="extended", font=("Segoe UI", 10), exportselection=False
        )
        self.listbox_preservar.pack(fill="both", expand=True)
        for col in self.available_columns:
            self.listbox_preservar.insert(tk.END, col)

        # --- Formato texto (solo impresión; útil si difiere de mantener_formato) ---
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

        # --- Botonera ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Limpiar", command=self._on_clear).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cargar por defecto", command=self._on_load_defaults).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Guardar", command=self._on_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=6)

    # ------------------------------------------------------------------ Carga inicial

    def _load_initial_selection(self) -> None:
        """
        Carga la selección inicial desde las REGLAS EFECTIVAS del modo (misma fuente que usa el pipeline).
        Esquema v2: reglas dentro de config["modes"][mode]; se usa get_effective_mode_rules para coalescer.
        """
        cfg = load_config()  # v2 ya mergeado/coalescido por config_manager
        rules = get_effective_mode_rules(self.mode, cfg)

        eliminar = list(rules.get("eliminar", []))
        sumar = list(rules.get("sumar", []))
        preservar = list(rules.get("mantener_formato", []))

        # En v2, formato_texto también vive en modes[mode]
        formato_texto = []
        modes = cfg.get("modes", {})
        if isinstance(modes, dict) and self.mode in modes:
            formato_texto = list(modes[self.mode].get("formato_texto", []) or [])

        start_row = int(rules.get("start_row", 0) or 0)

        # Aplica al UI
        self._apply_rules_to_ui(
            start_row=start_row,
            eliminar=eliminar,
            sumar=sumar,
            preservar=preservar,
            formato_texto=formato_texto,
        )

        log_evento(
            f"[CONFIG-UI] Inicial para '{self.mode}': start_row={start_row}, "
            f"eliminar={eliminar}, sumar={sumar}, mantener_formato={preservar}, formato_texto={formato_texto}",
            "info",
        )

    # ------------------------------------------------------------------ Helpers de UI

    def _apply_rules_to_ui(
        self,
        start_row: int,
        eliminar: List[str],
        sumar: List[str],
        preservar: List[str],
        formato_texto: List[str],
    ) -> None:
        """Refresca selección de listboxes y spinbox con las reglas dadas."""
        self.start_row_var.set(start_row)

        # Limpia selecciones actuales
        for lb in (self.listbox_eliminar, self.listbox_sumar, self.listbox_preservar, self.listbox_formato_texto):
            lb.selection_clear(0, tk.END)

        # Vuelve a marcar según reglas
        for idx, col in enumerate(self.available_columns):
            if col in eliminar:
                self.listbox_eliminar.select_set(idx)
            if col in sumar:
                self.listbox_sumar.select_set(idx)
            if col in preservar:
                self.listbox_preservar.select_set(idx)
            if col in formato_texto:
                self.listbox_formato_texto.select_set(idx)

    def _collect_from_ui(self) -> Dict[str, Any]:
        """Recoge la configuración desde los controles UI."""
        eliminar = [self.available_columns[i] for i in self.listbox_eliminar.curselection()]
        sumar = [self.available_columns[i] for i in self.listbox_sumar.curselection()]
        preservar = [self.available_columns[i] for i in self.listbox_preservar.curselection()]
        formato_texto = [self.available_columns[i] for i in self.listbox_formato_texto.curselection()]

        return {
            "start_row": int(self.start_row_var.get() or 0),
            "eliminar": eliminar,
            "sumar": sumar,
            "mantener_formato": preservar,
            "formato_texto": formato_texto,
        }

    # ------------------------------------------------------------------ Acciones de botones

    def _on_save(self) -> None:
        """
        Guarda SOLO el modo actual dentro de config['modes'][mode] (esquema v2).
        Conserva 'paths' y otros modos.
        """
        actual_mode_cfg = self._collect_from_ui()

        cfg_disk = load_config()
        if not isinstance(cfg_disk, dict):
            cfg_disk = {}

        # Asegurar contenedor v2
        cfg_disk.setdefault("version", 2)
        cfg_disk.setdefault("paths", cfg_disk.get("paths", {}))
        cfg_disk.setdefault("modes", {})
        if not isinstance(cfg_disk["modes"], dict):
            cfg_disk["modes"] = {}

        cfg_disk["modes"][self.mode] = actual_mode_cfg  # <-- v2 correcto

        ok = save_config(cfg_disk)
        if ok:
            # Mantén in-memory para el caller
            self.config_columns.setdefault("modes", {})
            self.config_columns["modes"][self.mode] = actual_mode_cfg
            log_evento(f"[CONFIG-UI] Guardado v2 para '{self.mode}': {actual_mode_cfg}", "info")
            messagebox.showinfo("Configuración", "Configuración guardada.")
            self.destroy()
        else:
            log_evento(f"[CONFIG-UI] Error al guardar configuración para '{self.mode}'", "error")
            messagebox.showerror("Configuración", "No se pudo guardar la configuración.")

    def _on_load_defaults(self) -> None:
        """
        Carga los valores por defecto SOLO para el modo actual desde excel_printer_default.json (v2)
        y los aplica al UI y los guarda en ~/.exelcior_apolo/config.json.
        """
        if not messagebox.askyesno(
            "Cargar por defecto",
            "¿Deseas cargar los valores por defecto para este modo y sobrescribir los actuales?"
        ):
            return

        try:
            defaults = self._read_defaults_from_file()

            # defaults puede venir en v2; si viniera legacy v1, se intenta mapear
            mode_defaults: Dict[str, Any] = {}
            if "modes" in defaults and isinstance(defaults["modes"], dict):
                mode_defaults = dict(defaults["modes"].get(self.mode, {}))
            else:
                # fallback v1 (claves por modo en top-level)
                mode_defaults = dict(defaults.get(self.mode, {}))

            rules = {
                "start_row": int(mode_defaults.get("start_row", 0) or 0),
                "eliminar": list(mode_defaults.get("eliminar", []) or []),
                "sumar": list(mode_defaults.get("sumar", []) or []),
                "mantener_formato": list(mode_defaults.get("mantener_formato", []) or []),
                "formato_texto": list(mode_defaults.get("formato_texto", []) or []),
            }

            # Aplica al UI
            self._apply_rules_to_ui(
                start_row=rules["start_row"],
                eliminar=rules["eliminar"],
                sumar=rules["sumar"],
                preservar=rules["mantener_formato"],
                formato_texto=rules["formato_texto"],
            )

            # Persiste a disco (v2)
            cfg_disk = load_config()
            cfg_disk.setdefault("version", 2)
            cfg_disk.setdefault("paths", cfg_disk.get("paths", {}))
            cfg_disk.setdefault("modes", {})
            cfg_disk["modes"][self.mode] = rules

            if save_config(cfg_disk):
                self.config_columns.setdefault("modes", {})
                self.config_columns["modes"][self.mode] = rules
                log_evento(f"[CONFIG-UI] Cargado POR DEFECTO v2 para '{self.mode}': {rules}", "info")
                messagebox.showinfo("Configuración", "Valores por defecto aplicados y guardados.")
            else:
                messagebox.showerror("Configuración", "No se pudo guardar la configuración por defecto.")
        except Exception as e:
            log_evento(f"[CONFIG-UI] Error cargando defaults: {e}", "error")
            messagebox.showerror("Configuración", f"No se pudieron cargar los valores por defecto:\n{e}")

    def _on_clear(self) -> None:
        """
        Limpia el modo actual (listas vacías, start_row = 0) y guarda en config['modes'][mode].
        """
        if not messagebox.askyesno(
            "Limpiar configuración",
            "¿Seguro que quieres limpiar TODA la configuración de este modo?"
        ):
            return

        rules = {
            "start_row": 0,
            "eliminar": [],
            "sumar": [],
            "mantener_formato": [],
            "formato_texto": [],
        }

        # Aplica al UI
        self._apply_rules_to_ui(
            start_row=0,
            eliminar=[],
            sumar=[],
            preservar=[],
            formato_texto=[],
        )

        # Persiste en v2
        cfg_disk = load_config()
        cfg_disk.setdefault("version", 2)
        cfg_disk.setdefault("paths", cfg_disk.get("paths", {}))
        cfg_disk.setdefault("modes", {})
        cfg_disk["modes"][self.mode] = rules

        if save_config(cfg_disk):
            self.config_columns.setdefault("modes", {})
            self.config_columns["modes"][self.mode] = rules
            log_evento(f"[CONFIG-UI] Limpieza aplicada (v2) para '{self.mode}'", "info")
            messagebox.showinfo("Configuración", "Configuración del modo limpiada.")
        else:
            messagebox.showerror("Configuración", "No se pudo guardar la limpieza de configuración.")

    # ------------------------------------------------------------------ Defaults helpers

    def _read_defaults_from_file(self) -> Dict[str, Any]:
        """
        Lee el JSON de defaults desde DEFAULT_CFG_PATH.
        Devuelve {} si no existe o si hay error de lectura.
        Acepta tanto v2 (preferido) como legacy v1.
        """
        try:
            p = Path(DEFAULT_CFG_PATH)
            if not p.exists():
                log_evento(f"[CONFIG-UI] No existe default en {p}", "warning")
                return {}
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                log_evento(f"[CONFIG-UI] Estructura default inválida (no dict) en {p}", "warning")
                return {}
            return data
        except Exception as e:
            log_evento(f"[CONFIG-UI] Error leyendo defaults {DEFAULT_CFG_PATH}: {e}", "error")
            return {}
