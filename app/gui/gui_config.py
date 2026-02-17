# app/gui/gui_config.py
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Any, Optional


def _parse_value(text: str) -> Any:
    """
    Convierte un string del formulario a un tipo útil:
    - JSON válido -> dict/list/num/bool/None
    - true/false   -> bool
    - int/float    -> números
    - si nada aplica -> str
    """
    if text is None:
        return ""
    s = text.strip()

    # JSON (dict/list/num/true/false/null)
    try:
        return json.loads(s)
    except Exception:
        pass

    low = s.lower()
    if low in ("true", "false"):
        return low == "true"

    try:
        return int(s)
    except Exception:
        pass

    try:
        return float(s)
    except Exception:
        pass

    return s


class ConfigSystemDialog(tk.Toplevel):
    """
    Editor general de configuración (clave -> valor).
    Muestra y permite editar las claves top-level de la configuración consolidada.
    Botones:
      - Guardar: persiste (merge superficial) sobre config de usuario
      - Cargar Default: rellena el formulario con el archivo default.json (no persiste hasta Guardar)
      - Limpiar: vacía todos los campos
      - Cancelar: cierra sin cambios
    """

    def __init__(
        self,
        parent: tk.Tk,
        initial_config: Dict[str, Any],
        default_config: Dict[str, Any],
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        super().__init__(parent)
        self.title("Ajustes del Sistema")
        self.geometry("640x520")
        self.configure(bg="#F9FAFB")
        self.resizable(True, True)

        self._parent = parent
        self._on_save = on_save
        self._default_config = default_config if isinstance(default_config, dict) else {}
        self._fields: Dict[str, tk.Entry] = {}

        self._build_form(initial_config)
        self._build_buttons()

        # UX: modal sobre la app
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    # ------------------- UI -------------------

    def _build_form(self, config: Dict[str, Any]) -> None:
        # contenedor con scroll por si hay muchas claves
        outer = tk.Frame(self, bg="#F9FAFB")
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(outer, bg="#F9FAFB", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#F9FAFB")

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # encabezados
        hdr = tk.Frame(inner, bg="#F9FAFB")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        tk.Label(hdr, text="Clave", bg="#F9FAFB", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(hdr, text="Valor", bg="#F9FAFB", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=220)

        # filas
        inner.grid_columnconfigure(0, weight=0)
        inner.grid_columnconfigure(1, weight=1)

        for r_idx, (key, value) in enumerate(config.items(), start=1):
            tk.Label(inner, text=str(key), bg="#F9FAFB", font=("Segoe UI", 10)).grid(
                row=r_idx, column=0, sticky="w", padx=(0, 12), pady=4
            )

            entry = ttk.Entry(inner, font=("Segoe UI", 10))
            entry.grid(row=r_idx, column=1, sticky="ew", pady=4)

            # dict/list -> JSON; resto -> str
            try:
                if isinstance(value, (dict, list)):
                    entry.insert(0, json.dumps(value, ensure_ascii=False))
                else:
                    entry.insert(0, "" if value is None else str(value))
            except Exception:
                entry.insert(0, "" if value is None else str(value))

            self._fields[key] = entry

        # recordatorio
        tip = tk.Label(
            inner,
            text="Sugerencia: para listas o diccionarios escribe JSON (ej. [\"a\",\"b\"] o {\"k\":1}).",
            bg="#F9FAFB",
            fg="#6B7280",
            font=("Segoe UI", 9, "italic"),
        )
        tip.grid(row=r_idx + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_buttons(self) -> None:
        btns = tk.Frame(self, bg="#F9FAFB")
        btns.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Cargar Default", command=self._load_default).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Limpiar", command=self._clear).pack(side=tk.LEFT, padx=5)

        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.RIGHT, padx=5)

    # ------------------- Acciones -------------------

    def _load_default(self) -> None:
        for key, entry in self._fields.items():
            entry.delete(0, tk.END)
            val = self._default_config.get(key, "")
            try:
                if isinstance(val, (dict, list)):
                    entry.insert(0, json.dumps(val, ensure_ascii=False))
                else:
                    entry.insert(0, "" if val is None else str(val))
            except Exception:
                entry.insert(0, "" if val is None else str(val))

    def _clear(self) -> None:
        for entry in self._fields.values():
            entry.delete(0, tk.END)

    def _save(self) -> None:
        # construye diccionario con lo que hay en el formulario
        edited: Dict[str, Any] = {}
        for key, entry in self._fields.items():
            edited[key] = _parse_value(entry.get())

        try:
            from app.config.config_manager import load_config, save_config
            current = load_config()
            if not isinstance(current, dict):
                current = {}

            # merge superficial
            current.update(edited)

            ok = save_config(current)
            if not ok:
                raise RuntimeError("No se pudo guardar la configuración de usuario.")

            if callable(self._on_save):
                self._on_save(current)

            # messagebox (si el padre expone helper seguro)
            if hasattr(self._parent, "safe_messagebox"):
                self._parent.safe_messagebox("info", "Guardado", "Configuración guardada correctamente.")
            self.destroy()
        except Exception as e:
            if hasattr(self._parent, "safe_messagebox"):
                self._parent.safe_messagebox("error", "Error", f"No se pudo guardar:\n{e}")

