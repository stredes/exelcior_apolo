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

        style.configure("PrinterShell.TFrame", background="#EEF2F8")
        style.configure("PrinterHero.TFrame", background="#17324A")
        style.configure("PrinterHeroKicker.TLabel", background="#17324A", foreground="#C9DDF2", font=("Segoe UI Semibold", 8))
        style.configure("PrinterHeroTitle.TLabel", background="#17324A", foreground="#FFFFFF", font=("Segoe UI Semibold", 17))
        style.configure("PrinterHeroSub.TLabel", background="#17324A", foreground="#A8C2DA", font=("Segoe UI", 9))
        style.configure("PrinterSection.TLabelframe", background="#FFFFFF")
        style.configure("PrinterSection.TLabelframe.Label", background="#FFFFFF", foreground="#17324A", font=("Segoe UI Semibold", 10))
        style.configure("PrinterBody.TLabel", background="#FFFFFF", foreground="#243B53", font=("Segoe UI", 10))
        style.configure("PrinterHint.TLabel", background="#FFFFFF", foreground="#627D98", font=("Segoe UI", 9))
        style.configure("PrinterShellHint.TLabel", background="#EEF2F8", foreground="#627D98", font=("Segoe UI", 9))
        style.configure("PrinterPrimary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("PrinterSecondary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("PrinterBadge.TLabel", background="#EAF4FF", foreground="#0F4C81", font=("Segoe UI Semibold", 9))

        shell = ttk.Frame(self, padding=14, style="PrinterShell.TFrame")
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        hero = ttk.Frame(shell, style="PrinterHero.TFrame", padding=14)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(hero, text="IMPRESION", style="PrinterHeroKicker.TLabel").pack(anchor="w")
        ttk.Label(hero, text="Administracion de dispositivos", style="PrinterHeroTitle.TLabel").pack(anchor="w", pady=(4, 2))
        ttk.Label(
            hero,
            text="Define que impresora se usa para reportes, modos operativos y etiquetado desde una sola pantalla.",
            style="PrinterHeroSub.TLabel",
        ).pack(anchor="w")

        actions = ttk.Frame(shell, style="PrinterShell.TFrame")
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(actions, text="Refrescar impresoras", style="PrinterPrimary.TButton", command=self._refresh_printers).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, style="PrinterBadge.TLabel", padding=(10, 6)).pack(side="left", padx=12)

        body = ttk.Frame(shell, style="PrinterShell.TFrame")
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Impresoras detectadas", padding=10, style="PrinterSection.TLabelframe")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ttk.LabelFrame(body, text="Asignacion operativa", padding=10, style="PrinterSection.TLabelframe")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        ttk.Label(
            left,
            text="Estas son las impresoras detectadas en el equipo. Puedes usarlas como referencia al configurar cada destino.",
            style="PrinterHint.TLabel",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        list_shell = tk.Frame(left, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D8E4EF")
        list_shell.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            list_shell,
            height=20,
            font=("Segoe UI", 10),
            bd=0,
            relief="flat",
            highlightthickness=0,
            selectbackground="#D9EAFE",
            selectforeground="#102A43",
            activestyle="none",
        )
        list_scroll = ttk.Scrollbar(list_shell, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=list_scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        list_scroll.pack(side="right", fill="y", pady=8, padx=(0, 8))

        ttk.Label(
            right,
            text="Cada modo puede heredar la impresora general o usar una distinta cuando la operación lo requiera.",
            style="PrinterHint.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))

        assignments = [
            ("Reportes (general):", "Se usa como impresora principal de respaldo.", self.report_var),
            ("Listados:", "Destino para documentos generales del modo listados.", self.listados_var),
            ("FedEx:", "Destino de impresión para salidas operativas FedEx.", self.fedex_var),
            ("Urbano:", "Destino de impresión para planillas y cierres Urbano.", self.urbano_var),
            ("Etiquetadora:", "Impresora dedicada a etiquetas y códigos.", self.label_var),
        ]

        for idx, (label, hint, var) in enumerate(assignments):
            block = ttk.Frame(right, style="PrinterShell.TFrame")
            block.grid(row=idx + 1, column=0, sticky="ew", pady=(0, 10))
            card = tk.Frame(block, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D8E4EF")
            card.pack(fill="x")
            ttk.Label(card, text=label, style="PrinterBody.TLabel").pack(anchor="w", padx=10, pady=(10, 2))
            ttk.Label(card, text=hint, style="PrinterHint.TLabel", wraplength=320, justify="left").pack(anchor="w", padx=10)
            combo = ttk.Combobox(card, textvariable=var, state="readonly", font=("Segoe UI", 10))
            combo.pack(fill="x", padx=10, pady=(8, 10))
            setattr(self, f"combo_{idx}", combo)

        footer = ttk.Frame(shell, style="PrinterShell.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(
            footer,
            text="La configuración se guarda de inmediato para los reportes, modos y etiquetadora.",
            style="PrinterShellHint.TLabel",
        ).pack(side="left")
        ttk.Button(footer, text="Cerrar", style="PrinterSecondary.TButton", command=self.destroy).pack(side="right")
        ttk.Button(footer, text="Guardar", style="PrinterPrimary.TButton", command=self._save).pack(side="right", padx=(0, 8))

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
