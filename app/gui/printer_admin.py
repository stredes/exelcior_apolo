from __future__ import annotations

import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List

from app.config.config_manager import load_config, save_config
from app.gui.etiqueta_editor import cargar_config as cargar_config_etiquetas
from app.gui.etiqueta_editor import guardar_config as guardar_config_etiquetas


def get_system_printers() -> List[str]:
    system = platform.system()
    printers: List[str] = []
    if system == "Windows":
        try:
            import win32print  # type: ignore

            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            raw = win32print.EnumPrinters(flags)
            names = []
            for item in raw:
                if isinstance(item, (tuple, list)) and len(item) >= 3:
                    names.append(str(item[2]))
                elif isinstance(item, dict) and item.get("pPrinterName"):
                    names.append(str(item.get("pPrinterName")))
            printers = sorted({n.strip() for n in names if n and n.strip()})
        except Exception:
            printers = []
    elif system == "Linux":
        try:
            output = subprocess.check_output(["lpstat", "-a"], text=True)
            printers = sorted({line.split()[0] for line in output.splitlines() if line.strip()})
        except Exception:
            printers = []
    return printers


class PrinterAdminDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Administracion de Dispositivos de Impresion")
        self.geometry("820x620")
        self.minsize(760, 560)
        self.configure(bg="#EEF2F8")
        self.transient(parent)

        self.printers: List[str] = []
        self.status_var = tk.StringVar(value="Cargando impresoras...")
        self.report_var = tk.StringVar(value="")
        self.listados_var = tk.StringVar(value="")
        self.fedex_var = tk.StringVar(value="")
        self.urbano_var = tk.StringVar(value="")
        self.label_var = tk.StringVar(value="")

        self._build_ui()
        self._load_initial_values()
        self._refresh_printers()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        shell = ttk.Frame(self, padding=14)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="Dispositivos de impresion", font=("Segoe UI Semibold", 16)).pack(anchor="w")
        ttk.Label(
            shell,
            text="Selecciona impresora para reportes y etiquetadora. La configuracion queda guardada.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 10))

        actions = ttk.Frame(shell)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Refrescar impresoras", command=self._refresh_printers).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var).pack(side="left", padx=12)

        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Impresoras detectadas", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ttk.LabelFrame(body, text="Asignacion", padding=10)
        right.grid(row=0, column=1, sticky="nsew")

        self.listbox = tk.Listbox(left, height=20, font=("Segoe UI", 10))
        self.listbox.pack(fill="both", expand=True)

        for idx, (label, var) in enumerate(
            [
                ("Reportes (general):", self.report_var),
                ("Listados:", self.listados_var),
                ("FedEx:", self.fedex_var),
                ("Urbano:", self.urbano_var),
                ("Etiquetadora:", self.label_var),
            ]
        ):
            ttk.Label(right, text=label).grid(row=idx * 2, column=0, sticky="w", pady=(0, 4))
            combo = ttk.Combobox(right, textvariable=var, state="readonly")
            combo.grid(row=idx * 2 + 1, column=0, sticky="ew", pady=(0, 12))
            setattr(self, f"combo_{idx}", combo)

        right.columnconfigure(0, weight=1)

        footer = ttk.Frame(shell)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Button(footer, text="Guardar", command=self._save).pack(side="right")
        ttk.Button(footer, text="Cerrar", command=self.destroy).pack(side="right", padx=(0, 8))

    def _load_initial_values(self) -> None:
        cfg = load_config() or {}
        mode_printers = cfg.get("mode_printers", {}) if isinstance(cfg.get("mode_printers"), dict) else {}

        report = (
            cfg.get("report_printer_name")
            or cfg.get("paper_printer_name")
            or cfg.get("paths", {}).get("default_printer", "")
        )
        self.report_var.set(str(report or ""))
        self.listados_var.set(str(mode_printers.get("listados", report or "")))
        self.fedex_var.set(str(mode_printers.get("fedex", report or "")))
        self.urbano_var.set(str(mode_printers.get("urbano", report or "")))

        label_cfg = cargar_config_etiquetas() or {}
        label = (
            cfg.get("label_printer_name")
            or cfg.get("printer_name")
            or label_cfg.get("label_printer_name")
            or label_cfg.get("printer_name")
            or ""
        )
        self.label_var.set(str(label))

    def _refresh_printers(self) -> None:
        printers = get_system_printers()
        self.printers = printers
        self.listbox.delete(0, tk.END)
        for p in printers:
            self.listbox.insert(tk.END, p)

        values = printers
        for i in range(5):
            combo = getattr(self, f"combo_{i}")
            combo["values"] = values

        if printers:
            self.status_var.set(f"Impresoras detectadas: {len(printers)}")
        else:
            self.status_var.set("No se detectaron impresoras.")

    def _save(self) -> None:
        report = self.report_var.get().strip()
        listados = self.listados_var.get().strip() or report
        fedex = self.fedex_var.get().strip() or report
        urbano = self.urbano_var.get().strip() or report
        label = self.label_var.get().strip()

        if not report:
            messagebox.showerror("Impresoras", "Debes seleccionar una impresora para reportes.")
            return
        if not label:
            messagebox.showerror("Impresoras", "Debes seleccionar una impresora etiquetadora.")
            return

        cfg = load_config() or {}
        cfg["report_printer_name"] = report
        cfg["paper_printer_name"] = report
        cfg["default_printer"] = report
        cfg["mode_printers"] = {
            "listados": listados,
            "fedex": fedex,
            "urbano": urbano,
        }
        cfg["label_printer_name"] = label
        cfg["printer_name"] = label
        cfg.setdefault("paths", {})
        cfg["paths"]["default_printer"] = report

        if not save_config(cfg):
            messagebox.showerror("Impresoras", "No se pudo guardar la configuracion.")
            return

        label_cfg = cargar_config_etiquetas() or {}
        label_cfg["label_printer_name"] = label
        label_cfg["printer_name"] = label
        try:
            guardar_config_etiquetas(label_cfg)
        except Exception:
            pass

        messagebox.showinfo("Impresoras", "Configuracion de impresoras guardada.")
        self.destroy()
