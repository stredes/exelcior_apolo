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
    DEFAULT_CFG_PATH,
)
from app.core.logger_eventos import log_evento


class ConfigDialog(tk.Toplevel):
    """
    Dialogo de configuracion por modo (compatible con esquema v2).
    Fuente de verdad: config_manager.
    """

    def __init__(
        self,
        parent: tk.Tk,
        mode: str,
        available_columns: List[str],
        config_columns: Dict[str, Any],
    ) -> None:
        super().__init__(parent)
        self.title(f"Configuracion - {mode.capitalize()}")
        self.geometry("980x760")
        self.configure(background="#EEF4F8")
        self.resizable(True, True)

        self.mode = (mode or "").strip().lower()
        self.available_columns = list(available_columns)
        self.config_columns = config_columns if isinstance(config_columns, dict) else {}

        self.start_row_var = tk.IntVar(value=0)
        self.summary_vars = {
            "eliminar": tk.StringVar(value="0 columnas"),
            "sumar": tk.StringVar(value="0 columnas"),
            "preservar": tk.StringVar(value="0 columnas"),
            "formato_texto": tk.StringVar(value="0 columnas"),
            "disponibles": tk.StringVar(value=f"{len(self.available_columns)} disponibles"),
            "inicio": tk.StringVar(value="Fila 0"),
        }

        self._configure_styles()
        self._create_widgets()
        self._load_initial_selection()

        self.transient(parent)
        self.grab_set()
        self.focus_set()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("CfgShell.TFrame", background="#EEF4F8")
        style.configure("CfgHero.TFrame", background="#17324A")
        style.configure("CfgHeroKicker.TLabel", background="#17324A", foreground="#C7DCF4", font=("Segoe UI Semibold", 8))
        style.configure("CfgHeroTitle.TLabel", background="#17324A", foreground="#FFFFFF", font=("Segoe UI Semibold", 17))
        style.configure("CfgHeroSub.TLabel", background="#17324A", foreground="#A9C6DF", font=("Segoe UI", 9))
        style.configure("CfgSection.TLabelframe", background="#FFFFFF")
        style.configure("CfgSection.TLabelframe.Label", background="#FFFFFF", foreground="#17324A", font=("Segoe UI Semibold", 10))
        style.configure("CfgBody.TLabel", background="#FFFFFF", foreground="#243B53", font=("Segoe UI", 10))
        style.configure("CfgHint.TLabel", background="#FFFFFF", foreground="#627D98", font=("Segoe UI", 9))
        style.configure("CfgMetric.TFrame", background="#FFFFFF")
        style.configure("CfgMetricValue.TLabel", background="#FFFFFF", foreground="#17324A", font=("Segoe UI Semibold", 15))
        style.configure("CfgMetricTitle.TLabel", background="#FFFFFF", foreground="#627D98", font=("Segoe UI", 9))
        style.configure("CfgPrimary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("CfgSecondary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))

    def _create_listbox_panel(self, parent, title: str, hint: str) -> tk.Listbox:
        frame = ttk.LabelFrame(parent, text=title, padding=10, style="CfgSection.TLabelframe")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=hint, style="CfgHint.TLabel").pack(anchor="w", pady=(0, 6))

        body = tk.Frame(frame, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D8E4EF")
        body.pack(fill="both", expand=True)

        lb = tk.Listbox(
            body,
            selectmode="extended",
            font=("Segoe UI", 10),
            exportselection=False,
            bd=0,
            relief="flat",
            highlightthickness=0,
            selectbackground="#D9EAFE",
            selectforeground="#102A43",
        )
        sb = ttk.Scrollbar(body, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side=tk.LEFT, fill="both", expand=True)
        sb.pack(side=tk.RIGHT, fill="y")
        for col in self.available_columns:
            lb.insert(tk.END, col)
        lb.bind("<<ListboxSelect>>", self._on_selection_change)
        return lb

    def _create_metric_card(self, parent, title: str, variable: tk.StringVar) -> None:
        card = ttk.Frame(parent, style="CfgMetric.TFrame", padding=12)
        card.pack(side=tk.LEFT, fill="both", expand=True, padx=4)
        ttk.Label(card, textvariable=variable, style="CfgMetricValue.TLabel").pack(anchor="w")
        ttk.Label(card, text=title, style="CfgMetricTitle.TLabel").pack(anchor="w", pady=(3, 0))

    def _create_widgets(self) -> None:
        shell = ttk.Frame(self, style="CfgShell.TFrame", padding=12)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)

        hero = ttk.Frame(shell, style="CfgHero.TFrame", padding=14)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(hero, text="CONFIGURACION DE MODO", style="CfgHeroKicker.TLabel").pack(anchor="w")
        ttk.Label(hero, text=self.mode.capitalize(), style="CfgHeroTitle.TLabel").pack(anchor="w", pady=(4, 2))
        ttk.Label(
            hero,
            text="Define que columnas se eliminan, cuales se suman y que campos deben conservar formato textual.",
            style="CfgHeroSub.TLabel",
        ).pack(anchor="w")

        top = ttk.LabelFrame(shell, text="Lectura inicial", padding=12, style="CfgSection.TLabelframe")
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(2, weight=1)
        ttk.Label(top, text="Fila de inicio:", style="CfgBody.TLabel").grid(row=0, column=0, sticky="w")
        self.spn_start_row = ttk.Spinbox(top, from_=0, to=10000, width=8, textvariable=self.start_row_var)
        self.spn_start_row.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(
            top,
            text="Las filas anteriores a este indice se omiten al leer el archivo del modo.",
            style="CfgHint.TLabel",
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Label(
            top,
            textvariable=self.summary_vars["disponibles"],
            style="CfgHint.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        summary = ttk.LabelFrame(shell, text="Resumen rapido", padding=10, style="CfgSection.TLabelframe")
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self._create_metric_card(summary, "Columnas a eliminar", self.summary_vars["eliminar"])
        self._create_metric_card(summary, "Columnas a sumar", self.summary_vars["sumar"])
        self._create_metric_card(summary, "Preservar como texto", self.summary_vars["preservar"])
        self._create_metric_card(summary, "Formato solo impresion", self.summary_vars["formato_texto"])
        self._create_metric_card(summary, "Lectura inicial", self.summary_vars["inicio"])

        grid = ttk.Frame(shell, style="CfgShell.TFrame")
        grid.grid(row=3, column=0, sticky="nsew")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

        cell_00 = ttk.Frame(grid, style="CfgShell.TFrame")
        cell_00.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.listbox_eliminar = self._create_listbox_panel(
            cell_00,
            "Columnas a eliminar",
            "Campos que no deben aparecer en la salida final.",
        )

        cell_01 = ttk.Frame(grid, style="CfgShell.TFrame")
        cell_01.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.listbox_sumar = self._create_listbox_panel(
            cell_01,
            "Columnas para sumatorias",
            "Se convierten a numerico antes de sumar.",
        )

        cell_10 = ttk.Frame(grid, style="CfgShell.TFrame")
        cell_10.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.listbox_preservar = self._create_listbox_panel(
            cell_10,
            "Preservar como texto",
            "Util para codigos, folios o identificadores sensibles al formato.",
        )

        cell_11 = ttk.Frame(grid, style="CfgShell.TFrame")
        cell_11.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        self.listbox_formato_texto = self._create_listbox_panel(
            cell_11,
            "Formato texto (solo impresion)",
            "Se aplica solo en impresion para mantener una salida visual consistente.",
        )

        btn_frame = ttk.Frame(shell, style="CfgShell.TFrame")
        btn_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(
            btn_frame,
            text="Los cambios se guardan solo para este modo y se aplican en la siguiente lectura.",
            style="CfgHint.TLabel",
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Limpiar", style="CfgSecondary.TButton", command=self._on_clear).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cargar por defecto", style="CfgSecondary.TButton", command=self._on_load_defaults).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancelar", style="CfgSecondary.TButton", command=self.destroy).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Guardar", style="CfgPrimary.TButton", command=self._on_save).pack(side=tk.LEFT, padx=6)

        self.start_row_var.trace_add("write", self._on_start_row_change)

    def _load_initial_selection(self) -> None:
        cfg = load_config()
        rules = get_effective_mode_rules(self.mode, cfg)

        eliminar = list(rules.get("eliminar", []))
        sumar = list(rules.get("sumar", []))
        preservar = list(rules.get("mantener_formato", []))

        formato_texto = []
        modes = cfg.get("modes", {})
        if isinstance(modes, dict) and self.mode in modes:
            formato_texto = list(modes[self.mode].get("formato_texto", []) or [])

        start_row = int(rules.get("start_row", 0) or 0)

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

    def _apply_rules_to_ui(
        self,
        start_row: int,
        eliminar: List[str],
        sumar: List[str],
        preservar: List[str],
        formato_texto: List[str],
    ) -> None:
        self.start_row_var.set(start_row)

        for lb in (self.listbox_eliminar, self.listbox_sumar, self.listbox_preservar, self.listbox_formato_texto):
            lb.selection_clear(0, tk.END)

        for idx, col in enumerate(self.available_columns):
            if col in eliminar:
                self.listbox_eliminar.select_set(idx)
            if col in sumar:
                self.listbox_sumar.select_set(idx)
            if col in preservar:
                self.listbox_preservar.select_set(idx)
            if col in formato_texto:
                self.listbox_formato_texto.select_set(idx)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        self.summary_vars["eliminar"].set(f"{len(self.listbox_eliminar.curselection())} columnas")
        self.summary_vars["sumar"].set(f"{len(self.listbox_sumar.curselection())} columnas")
        self.summary_vars["preservar"].set(f"{len(self.listbox_preservar.curselection())} columnas")
        self.summary_vars["formato_texto"].set(f"{len(self.listbox_formato_texto.curselection())} columnas")
        self.summary_vars["inicio"].set(f"Fila {int(self.start_row_var.get() or 0)}")

    def _on_selection_change(self, _event=None) -> None:
        self._refresh_summary()

    def _on_start_row_change(self, *_args) -> None:
        self._refresh_summary()

    def _collect_from_ui(self) -> Dict[str, Any]:
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

    def _on_save(self) -> None:
        actual_mode_cfg = self._collect_from_ui()

        cfg_disk = load_config()
        if not isinstance(cfg_disk, dict):
            cfg_disk = {}

        cfg_disk.setdefault("version", 2)
        cfg_disk.setdefault("paths", cfg_disk.get("paths", {}))
        cfg_disk.setdefault("modes", {})
        if not isinstance(cfg_disk["modes"], dict):
            cfg_disk["modes"] = {}

        cfg_disk["modes"][self.mode] = actual_mode_cfg

        ok = save_config(cfg_disk)
        if ok:
            self.config_columns.setdefault("modes", {})
            self.config_columns["modes"][self.mode] = actual_mode_cfg
            log_evento(f"[CONFIG-UI] Guardado v2 para '{self.mode}': {actual_mode_cfg}", "info")
            messagebox.showinfo("Configuracion", "Configuracion guardada.")
            self.destroy()
        else:
            log_evento(f"[CONFIG-UI] Error al guardar configuracion para '{self.mode}'", "error")
            messagebox.showerror("Configuracion", "No se pudo guardar la configuracion.")

    def _on_load_defaults(self) -> None:
        if not messagebox.askyesno(
            "Cargar por defecto",
            "Deseas cargar los valores por defecto para este modo y sobrescribir los actuales?",
        ):
            return

        try:
            defaults = self._read_defaults_from_file()

            mode_defaults: Dict[str, Any] = {}
            if "modes" in defaults and isinstance(defaults["modes"], dict):
                mode_defaults = dict(defaults["modes"].get(self.mode, {}))
            else:
                mode_defaults = dict(defaults.get(self.mode, {}))

            rules = {
                "start_row": int(mode_defaults.get("start_row", 0) or 0),
                "eliminar": list(mode_defaults.get("eliminar", []) or []),
                "sumar": list(mode_defaults.get("sumar", []) or []),
                "mantener_formato": list(mode_defaults.get("mantener_formato", []) or []),
                "formato_texto": list(mode_defaults.get("formato_texto", []) or []),
            }

            self._apply_rules_to_ui(
                start_row=rules["start_row"],
                eliminar=rules["eliminar"],
                sumar=rules["sumar"],
                preservar=rules["mantener_formato"],
                formato_texto=rules["formato_texto"],
            )

            cfg_disk = load_config()
            cfg_disk.setdefault("version", 2)
            cfg_disk.setdefault("paths", cfg_disk.get("paths", {}))
            cfg_disk.setdefault("modes", {})
            cfg_disk["modes"][self.mode] = rules

            if save_config(cfg_disk):
                self.config_columns.setdefault("modes", {})
                self.config_columns["modes"][self.mode] = rules
                log_evento(f"[CONFIG-UI] Cargado POR DEFECTO v2 para '{self.mode}': {rules}", "info")
                messagebox.showinfo("Configuracion", "Valores por defecto aplicados y guardados.")
            else:
                messagebox.showerror("Configuracion", "No se pudo guardar la configuracion por defecto.")
        except Exception as e:
            log_evento(f"[CONFIG-UI] Error cargando defaults: {e}", "error")
            messagebox.showerror("Configuracion", f"No se pudieron cargar los valores por defecto:\n{e}")

    def _on_clear(self) -> None:
        if not messagebox.askyesno(
            "Limpiar configuracion",
            "Seguro que quieres limpiar toda la configuracion de este modo?",
        ):
            return

        rules = {
            "start_row": 0,
            "eliminar": [],
            "sumar": [],
            "mantener_formato": [],
            "formato_texto": [],
        }

        self._apply_rules_to_ui(
            start_row=0,
            eliminar=[],
            sumar=[],
            preservar=[],
            formato_texto=[],
        )

        cfg_disk = load_config()
        cfg_disk.setdefault("version", 2)
        cfg_disk.setdefault("paths", cfg_disk.get("paths", {}))
        cfg_disk.setdefault("modes", {})
        cfg_disk["modes"][self.mode] = rules

        if save_config(cfg_disk):
            self.config_columns.setdefault("modes", {})
            self.config_columns["modes"][self.mode] = rules
            log_evento(f"[CONFIG-UI] Limpieza aplicada (v2) para '{self.mode}'", "info")
            messagebox.showinfo("Configuracion", "Configuracion del modo limpiada.")
        else:
            messagebox.showerror("Configuracion", "No se pudo guardar la limpieza de configuracion.")

    def _read_defaults_from_file(self) -> Dict[str, Any]:
        try:
            p = Path(DEFAULT_CFG_PATH)
            if not p.exists():
                log_evento(f"[CONFIG-UI] No existe default en {p}", "warning")
                return {}
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                log_evento(f"[CONFIG-UI] Estructura default invalida (no dict) en {p}", "warning")
                return {}
            return data
        except Exception as e:
            log_evento(f"[CONFIG-UI] Error leyendo defaults {DEFAULT_CFG_PATH}: {e}", "error")
            return {}
