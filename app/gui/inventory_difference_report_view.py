from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.core.logger_eventos import capturar_log_bod1
from app.services.inventory_difference_service import (
    export_inventory_difference_report,
    export_inventory_difference_report_pdf,
    get_inventory_difference_output_dir,
    get_inventory_difference_summary,
    get_inventory_differences_df,
)


class InventoryDifferenceReportView(tk.Toplevel):
    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("Informe de diferencias de stock")
        self.geometry("720x340")
        self.minsize(640, 300)
        self.configure(bg="#EEF2F8")

        self.summary_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value="")

        self._build_ui()
        self._refresh_summary()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        shell = ttk.Frame(self, padding=16)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="Informe de diferencias de stock", font=("Segoe UI Semibold", 15)).pack(anchor="w")
        ttk.Label(
            shell,
            text="Atajo rápido para exportar el ciclo activo en Excel o PDF sin entrar a la vista completa de inventario.",
        ).pack(anchor="w", pady=(4, 12))

        info = ttk.LabelFrame(shell, text="Ciclo activo", padding=12)
        info.pack(fill="x")
        ttk.Label(info, textvariable=self.summary_var, font=("Segoe UI Semibold", 10)).pack(anchor="w")
        ttk.Label(info, textvariable=self.detail_var, wraplength=640, justify="left").pack(anchor="w", pady=(6, 0))
        ttk.Label(info, textvariable=self.output_dir_var, wraplength=640, justify="left").pack(anchor="w", pady=(6, 0))

        actions = ttk.LabelFrame(shell, text="Exportación", padding=12)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Exportar Excel", command=self._export_excel).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Exportar PDF", command=self._export_pdf).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Actualizar resumen", command=self._refresh_summary).pack(side="left")

        footer = ttk.Frame(shell)
        footer.pack(fill="x", pady=(14, 0))
        ttk.Button(footer, text="Cerrar", command=self.destroy).pack(side="right")

    def _refresh_summary(self) -> None:
        diff_df = get_inventory_differences_df()
        summary = get_inventory_difference_summary(diff_df)
        self.summary_var.set(
            f"Registros activos: {summary['items']} | +{summary['positive_items']} | -{summary['negative_items']} | neto {summary['net_difference']:+d}"
        )
        if diff_df.empty:
            self.detail_var.set("No hay diferencias activas en este momento.")
        else:
            self.detail_var.set(
                "El informe incluirá código, producto, bodega, ubicación, lote/serie, stock sistema, diferencia, stock contado, observación y fecha."
            )
        self.output_dir_var.set(f"Carpeta sugerida: {get_inventory_difference_output_dir()}")

    def _export_excel(self) -> None:
        self._export_report(kind="excel")

    def _export_pdf(self) -> None:
        self._export_report(kind="pdf")

    def _export_report(self, kind: str) -> None:
        diff_df = get_inventory_differences_df()
        if diff_df.empty:
            messagebox.showinfo("Informe", "Todavía no hay diferencias activas para exportar.", parent=self)
            return

        base_dir = get_inventory_difference_output_dir()
        if kind == "pdf":
            destination = filedialog.asksaveasfilename(
                parent=self,
                title="Guardar informe de diferencias en PDF",
                defaultextension=".pdf",
                initialdir=str(base_dir),
                initialfile="informe_diferencias_stock.pdf",
                filetypes=[("PDF", "*.pdf")],
            )
        else:
            destination = filedialog.asksaveasfilename(
                parent=self,
                title="Guardar informe de diferencias en Excel",
                defaultextension=".xlsx",
                initialdir=str(base_dir),
                initialfile="informe_diferencias_stock.xlsx",
                filetypes=[("Excel", "*.xlsx")],
            )
        if not destination:
            return

        try:
            if kind == "pdf":
                path = export_inventory_difference_report_pdf(destination, diff_df=diff_df)
            else:
                path = export_inventory_difference_report(destination, diff_df=diff_df)
            capturar_log_bod1(f"[Inventario] Informe de diferencias exportado ({kind}) en {path}", "info")
            messagebox.showinfo("Informe", f"Informe generado correctamente en:\n{path}", parent=self)
        except Exception as e:
            capturar_log_bod1(f"[Inventario] Error exportando informe de diferencias ({kind}): {e}", "error")
            messagebox.showerror("Informe", f"No se pudo generar el informe:\n{e}", parent=self)
