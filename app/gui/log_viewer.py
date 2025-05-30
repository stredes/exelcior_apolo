import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


class LogViewer(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Visor de Logs")
        self.geometry("1000x600")
        self.configure(bg="#F9FAFB")

        self.log_dir = Path("logs")
        self.logs = []

        self._setup_ui()
        self._load_logs()

    def _setup_ui(self):
        container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Panel Izquierdo: Lista de Logs
        self.tree_frame = ttk.Frame(container)
        self.tree = ttk.Treeview(self.tree_frame, columns=("Archivo", "Tamaño"), show="headings", height=20)
        self.tree.heading("Archivo", text="Archivo")
        self.tree.heading("Tamaño", text="Tamaño")
        self.tree.column("Archivo", width=200)
        self.tree.column("Tamaño", width=100, anchor=tk.E)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._mostrar_contenido_log)
        container.add(self.tree_frame, weight=1)

        # Panel Derecho: Contenido del Log
        self.text_frame = ttk.Frame(container)
        self.text = tk.Text(self.text_frame, wrap=tk.NONE)
        self.text_scroll_y = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text_scroll_x = ttk.Scrollbar(self.text_frame, orient=tk.HORIZONTAL, command=self.text.xview)

        self.text.configure(yscrollcommand=self.text_scroll_y.set, xscrollcommand=self.text_scroll_x.set)

        self.text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.text_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        container.add(self.text_frame, weight=3)

    def _load_logs(self):
        if not self.log_dir.exists():
            messagebox.showinfo("Logs", "No hay logs para mostrar.")
            return

        self.logs = sorted(self.log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        for log in self.logs:
            size_kb = log.stat().st_size // 1024
            self.tree.insert("", "end", values=(log.name, f"{size_kb} KB"))

    def _mostrar_contenido_log(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        log_name = item["values"][0]
        log_path = self.log_dir / log_name

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                contenido = f.read()
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, contenido)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
