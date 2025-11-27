#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interfaz de Vales de Consumo (Bioplates) en ASCII seguro (sin emojis) para
evitar texto corrupto en Windows. Incluye:
- Filtros a la derecha con scroll
- Vale en curso con acciones
- Historial con abrir, reimprimir y unificar varios PDFs
- run_app() como punto de entrada
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

from config import INVENTORY_FILE, AREA_FILTER, HISTORY_DIR, WINDOWS_OS
from vale_manager import ValeManager
from filters import FilterOptions
from printing_utils import print_pdf_windows
import settings_store as settings
from vale_registry import ValeRegistry


class ValeConsumoApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Vale de Consumo - Bioplates")
        try:
            self.master.state('zoomed')
        except Exception:
            self.master.geometry('1280x800')

        self.manager = ValeManager()
        # Carpeta de historial desde ajustes (fallback a config)
        try:
            self.history_dir = settings.get_history_dir() or HISTORY_DIR
        except Exception:
            self.history_dir = HISTORY_DIR
        self.registry = ValeRegistry(self.history_dir)
        self.filtered_df: pd.DataFrame = pd.DataFrame()
        self.current_file: Optional[str] = None

        style = ttk.Style(self.master)
        try:
            # Tema y escalado suave en pantallas densas
            try:
                style.theme_use('clam')
            except Exception:
                pass
            try:
                # 1.15ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ1.25 suele ser cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³modo para 1080p/2k
                self.master.tk.call('tk', 'scaling', 1.15)
            except Exception:
                pass

            # TipografÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­as y colores base
            base_font = ('Segoe UI', 10)
            style.configure('TLabel', font=base_font)
            style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
            style.configure('TButton', font=base_font)
            style.configure('Treeview', font=base_font, rowheight=24, background='#ffffff', fieldbackground='#ffffff')
            style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=(6, 4), background='#f0f0f0')
            style.map('Treeview', background=[('selected', '#e1ecff')], foreground=[('selected', '#000000')])

            # BotÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de acciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n acentuado
            style.configure('Accent.TButton', background='#4a90e2', foreground='#ffffff')
            style.map('Accent.TButton', background=[('active', '#3d7fcc'), ('pressed', '#346dac')])
        except Exception:
            pass

        self._build_menu()

        container = ttk.Frame(self.master)
        container.grid(row=0, column=0, sticky='nsew')
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=0)  # topbar
        container.rowconfigure(1, weight=3)  # productos
        container.rowconfigure(2, weight=4)  # vale/historial
        container.columnconfigure(0, weight=1)

        # Barra superior: seleccion de archivo + recordatorio
        self.topbar = ttk.Frame(container, padding=(8, 6))
        self.topbar.grid(row=0, column=0, sticky='ew')
        self.topbar.columnconfigure(1, weight=1)

        self.select_btn = ttk.Button(self.topbar, text="Seleccionar archivo de inventario...", command=self.select_inventory_file)
        self.select_btn.grid(row=0, column=0, sticky='w', padx=(0, 10))

        self.file_label = ttk.Label(self.topbar, text="(ningun archivo cargado)")
        self.file_label.grid(row=0, column=1, sticky='w')

        # Acceso rapido a instrucciones
        try:
            self.topbar.columnconfigure(2, weight=0)
            ttk.Button(self.topbar, text="Instrucciones", command=self._open_instructions).grid(row=0, column=2, sticky='e')
        except Exception:
            pass

        if settings.get_reminder_enabled():
            lbl_txt = settings.get_reminder_text()
            self.reminder_label = ttk.Label(self.topbar, text=lbl_txt, foreground="#666666")
            self.reminder_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=(4, 0))
        else:
            self.reminder_label = None

        # Area superior: productos + filtros
        self._build_products_area(container)
        # Area inferior: Notebook Vale / Historial
        self._build_vale_and_history(container)

        # Atajos de teclado globales
        try:
            self.master.bind('<Control-f>', lambda e: self.search_entry.focus_set())
            self.master.bind('<Control-h>', lambda e: self.vale_notebook.select(self.hist_tab))
            self.master.bind('<Control-m>', lambda e: self.vale_notebook.select(self.mgr_tab))
            self.master.bind('<Control-g>', lambda e: self.generate_and_print_vale())
            # Suprimir item seleccionado del vale con tecla Supr
            try:
                self.vale_tree.bind('<Delete>', lambda e: self.remove_from_vale())
            except Exception:
                pass
        except Exception:
            pass

        # Carga automática del último archivo de inventario usado (si existe)
        try:
            last_file = settings.get_last_inventory_file()
        except Exception:
            last_file = None
        if last_file:
            self.current_file = last_file
            self._load_inventory(last_file)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        m_archivo = tk.Menu(menubar, tearoff=0)
        m_archivo.add_command(label="Seleccionar inventario...", command=self.select_inventory_file)
        m_archivo.add_separator()
        m_archivo.add_command(label="Salir", command=self.master.destroy)
        menubar.add_cascade(label="Archivo", menu=m_archivo)

        m_conf = tk.Menu(menubar, tearoff=0)
        m_conf.add_command(label="Ajustes...", command=self._open_settings_dialog)
        m_conf.add_separator()
        m_conf.add_command(label="Configuracion de impresora...", command=self._menu_printer_settings)
        m_conf.add_command(label="Herramientas de lectura de label...", command=self._menu_label_tools)
        menubar.add_cascade(label="Configuracion", menu=m_conf)

        # Menu Ayuda
        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Instrucciones de uso...", command=self._open_instructions)
        m_help.add_command(label="Atajos de teclado...", command=self._open_shortcuts)
        menubar.add_cascade(label="Ayuda", menu=m_help)

    def _menu_printer_settings(self) -> None:
        messagebox.showinfo(
            "Impresora",
            "Impresion automatica usa SumatraPDF si esta disponible.\n"
            "Configure SUMATRA_PDF_PATH en config.py o settings_store si desea forzar ruta."
        )

    def _menu_label_tools(self) -> None:
        messagebox.showinfo(
            "Lector de Label",
            "Proximamente: utilidades para probar y configurar el lector de etiquetas."
        )

    def _open_settings_dialog(self) -> None:
        dlg = tk.Toplevel(self.master)
        dlg.title('Ajustes')
        dlg.transient(self.master)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=12)
        frm.grid(row=0, column=0, sticky='nsew')
        dlg.columnconfigure(0, weight=1)
        dlg.rowconfigure(0, weight=1)

        # Vars
        ap_var = tk.BooleanVar(value=settings.get_auto_print())
        try:
            from config import SUMATRA_PDF_PATH as CFG_SUM
        except Exception:
            CFG_SUM = ''
        sum_var = tk.StringVar(value=(settings.get_sumatra_path() or CFG_SUM or ''))
        rem_en_var = tk.BooleanVar(value=settings.get_reminder_enabled())
        rem_text_var = tk.StringVar(value=settings.get_reminder_text())
        hist_var = tk.StringVar(value=(settings.get_history_dir()))

        r = 0
        ttk.Checkbutton(frm, text='Impresion automatica al generar', variable=ap_var).grid(row=r, column=0, columnspan=3, sticky='w')
        r += 1

        ttk.Label(frm, text='Ruta SumatraPDF.exe (opcional):').grid(row=r, column=0, sticky='w', pady=(8,0))
        e_sum = ttk.Entry(frm, textvariable=sum_var, width=60)
        e_sum.grid(row=r, column=1, sticky='ew', padx=(8,6), pady=(8,0))
        ttk.Button(frm, text='Examinar...', command=lambda: sum_var.set(filedialog.askopenfilename(title='Seleccionar SumatraPDF.exe', filetypes=[('Ejecutable','*.exe')]) or sum_var.get())).grid(row=r, column=2, sticky='w', pady=(8,0))
        r += 1

        ttk.Checkbutton(frm, text='Mostrar recordatorio superior', variable=rem_en_var).grid(row=r, column=0, columnspan=3, sticky='w', pady=(8,0))
        r += 1
        ttk.Label(frm, text='Texto del recordatorio:').grid(row=r, column=0, sticky='w')
        e_rem = ttk.Entry(frm, textvariable=rem_text_var, width=60)
        e_rem.grid(row=r, column=1, columnspan=2, sticky='ew', padx=(8,0))
        r += 1

        ttk.Label(frm, text='Carpeta Historial de vales:').grid(row=r, column=0, sticky='w', pady=(8,0))
        e_hist = ttk.Entry(frm, textvariable=hist_var, width=60)
        e_hist.grid(row=r, column=1, sticky='ew', padx=(8,6), pady=(8,0))
        ttk.Button(frm, text='Seleccionar...', command=lambda: hist_var.set(filedialog.askdirectory(title='Seleccionar carpeta de historial') or hist_var.get())).grid(row=r, column=2, sticky='w', pady=(8,0))
        r += 1

        for c in range(0,3):
            frm.columnconfigure(c, weight=(1 if c==1 else 0))

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=3, sticky='e', pady=(12,0))
        def _on_save():
            try:
                # Persistir
                settings.set_auto_print(bool(ap_var.get()))
                settings.set_sumatra_path(sum_var.get().strip())
                settings.set_reminder_enabled(bool(rem_en_var.get()))
                settings.set_reminder_text(rem_text_var.get())
                new_hist = hist_var.get().strip()
                if new_hist:
                    settings.set_history_dir(new_hist)
                # Aplicar en runtime
                try:
                    import config as _cfg
                    _cfg.SUMATRA_PDF_PATH = sum_var.get().strip()
                except Exception:
                    pass
                # Recordatorio en UI
                try:
                    if rem_en_var.get():
                        if not self.reminder_label:
                            self.reminder_label = ttk.Label(self.topbar, text=rem_text_var.get(), foreground="#666666")
                            self.reminder_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=(4, 0))
                        else:
                            self.reminder_label.configure(text=rem_text_var.get())
                    else:
                        if self.reminder_label:
                            self.reminder_label.destroy()
                            self.reminder_label = None
                except Exception:
                    pass
                # Historial (reubicar si cambio)
                try:
                    new_dir = settings.get_history_dir()
                    if new_dir and new_dir != getattr(self, 'history_dir', None):
                        self.history_dir = new_dir
                        os.makedirs(self.history_dir, exist_ok=True)
                        self.registry = ValeRegistry(self.history_dir)
                    self.refresh_history()
                    try:
                        self.refresh_manager()
                    except Exception:
                        pass
                except Exception:
                    pass
            finally:
                dlg.destroy()

        ttk.Button(btns, text='Guardar', command=_on_save).pack(side='right')
        ttk.Button(btns, text='Cancelar', command=dlg.destroy).pack(side='right', padx=(0,8))

    # --- Ayuda / Instrucciones ---
    def _open_instructions(self) -> None:
        text = None
        # Buscar instrucciones.txt en carpeta del script o cwd; fallback a texto embebido
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(here, 'instrucciones.txt'),
                os.path.join(os.getcwd(), 'instrucciones.txt')
            ]
            for p in candidates:
                if os.path.exists(p):
                    with open(p, 'r', encoding='utf-8') as f:
                        text = f.read()
                        break
        except Exception:
            text = None
        if not text:
            text = (
                "Uso basico:\n\n"
                "1) Seleccione el archivo de inventario (Excel).\n"
                "2) Aplique filtros (producto, subfamilia, lote, ubicacion, fechas).\n"
                "3) Ingrese cantidad y pulse 'Agregar al Vale'.\n"
                "4) Pulse 'Generar e Imprimir Vale' para crear el PDF.\n\n"
                "Historial y Manager:\n"
                "- En Historial: abrir, reimprimir y unificar varios vales.\n"
                "- En Manager: cambiar estados (Pendiente/Descontado/Anulado) y exportar listados.\n\n"
                "Ajustes:\n"
                "- Impresion automatica, ruta SumatraPDF, recordatorio y carpeta de historial.\n"
            )
        dlg = tk.Toplevel(self.master)
        dlg.title('Instrucciones de uso')
        dlg.geometry('820x520')
        dlg.transient(self.master)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill='both', expand=True)
        txt = tk.Text(frm, wrap='word')
        ysb = ttk.Scrollbar(frm, orient='vertical', command=txt.yview)
        txt.configure(yscrollcommand=ysb.set)
        txt.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')
        try:
            txt.insert('1.0', text)
        except Exception:
            txt.insert('1.0', 'No se pudieron cargar las instrucciones.')
        txt.configure(state='disabled')

    def _open_shortcuts(self) -> None:
        info = (
            "Atajos de teclado:\n\n"
            "Ctrl+F : Enfocar busqueda de productos\n"
            "Ctrl+H : Ir a pestaña Historial\n"
            "Ctrl+M : Ir a pestaña Manager Vales\n"
            "Ctrl+G : Generar e Imprimir Vale\n"
            "Supr   : Eliminar item seleccionado del vale\n"
        )
        messagebox.showinfo('Atajos de teclado', info)

    # -------- Productos y filtros --------
    def _build_products_area(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, padding=(8, 0))
        frame.grid(row=1, column=0, sticky='nsew')
        frame.columnconfigure(0, weight=1)

        # Tabla a la izquierda
        table_frame = ttk.Frame(frame)
        table_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        self.product_tree = ttk.Treeview(
            table_frame,
            columns=("Producto", "Lote", "Ubicacion", "Vencimiento", "Stock"),
            show='headings',
            selectmode='browse'
        )
        self.product_tree.heading('Producto', text='Producto')
        self.product_tree.heading('Lote', text='Lote')
        self.product_tree.heading('Ubicacion', text='Ubicacion')
        self.product_tree.heading('Vencimiento', text='Vencimiento')
        self.product_tree.heading('Stock', text='Stock')

        self.product_tree.column('Producto', width=280, minwidth=220, anchor='w', stretch=True)
        self.product_tree.column('Lote', width=120, minwidth=90, anchor='center', stretch=True)
        self.product_tree.column('Ubicacion', width=160, minwidth=120, anchor='center', stretch=True)
        self.product_tree.column('Vencimiento', width=130, minwidth=110, anchor='center', stretch=True)
        self.product_tree.column('Stock', width=80, minwidth=60, anchor='center', stretch=True)

        self.product_tree.grid(row=0, column=0, sticky='nsew')
        table_frame.rowconfigure(1, weight=1)
        table_frame.columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.product_tree.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        hsb = ttk.Scrollbar(table_frame, orient='horizontal', command=self.product_tree.xview)
        hsb.grid(row=1, column=0, sticky='ew')
        self.product_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.product_tree.bind('<Configure>', self._autosize_product_columns)

        # Panel de control con scroll
        filters_lf = ttk.LabelFrame(frame, text="Filtros y Acciones", padding=0, width=260)
        filters_lf.grid(row=0, column=1, sticky='ns')
        try:
            filters_lf.grid_propagate(False)
        except Exception:
            pass

        filters_canvas = tk.Canvas(filters_lf, borderwidth=0, highlightthickness=0)
        filters_vsb = ttk.Scrollbar(filters_lf, orient='vertical', command=filters_canvas.yview)
        filters_canvas.configure(yscrollcommand=filters_vsb.set)
        filters_vsb.pack(side='right', fill='y')
        filters_canvas.pack(side='left', fill='both', expand=True)

        self.control_frame = ttk.Frame(filters_canvas, padding=10)
        self._filters_window = filters_canvas.create_window((0, 0), window=self.control_frame, anchor='nw')

        def _on_cf_configure(event):
            try:
                filters_canvas.configure(scrollregion=filters_canvas.bbox('all'))
            except Exception:
                pass

        def _on_canvas_configure(event):
            try:
                filters_canvas.itemconfigure(self._filters_window, width=event.width)
            except Exception:
                pass

        self.control_frame.bind('<Configure>', _on_cf_configure)
        filters_canvas.bind('<Configure>', _on_canvas_configure)

        # Rueda del mouse sobre el panel
        def _on_mousewheel(event):
            try:
                delta = 0
                if hasattr(event, 'delta') and event.delta:
                    delta = int(-1 * (event.delta / 120))
                elif getattr(event, 'num', None) == 4:
                    delta = -1
                elif getattr(event, 'num', None) == 5:
                    delta = 1
                if delta:
                    filters_canvas.yview_scroll(delta, 'units')
            except Exception:
                pass

        filters_lf.bind('<Enter>', lambda e: filters_canvas.bind_all('<MouseWheel>', _on_mousewheel))
        filters_lf.bind('<Leave>', lambda e: filters_canvas.unbind_all('<MouseWheel>'))

        # Buscar
        ttk.Label(self.control_frame, text="Buscar producto:").grid(row=0, column=0, sticky='w', pady=(0, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.control_frame, textvariable=self.search_var, width=28)
        self.search_entry.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        self.search_var.trace_add('write', lambda *_: self.filter_products())

        # Cantidad y acciones
        ttk.Label(self.control_frame, text="Cantidad a retirar:").grid(row=2, column=0, sticky='w')
        self.quantity_entry = ttk.Entry(self.control_frame, width=10)
        self.quantity_entry.insert(0, '1')
        self.quantity_entry.grid(row=3, column=0, sticky='w', pady=(0, 6))
        ttk.Button(self.control_frame, text="Agregar al Vale", style='Accent.TButton', command=self.add_to_vale, width=26).grid(row=4, column=0, sticky='ew', pady=(4, 4))
        ttk.Button(self.control_frame, text="Generar e Imprimir Vale", style='Accent.TButton', command=self.generate_and_print_vale, width=26).grid(row=5, column=0, sticky='ew', pady=(2, 8))

        # Subfamilia
        ttk.Label(self.control_frame, text="Subfamilia:").grid(row=6, column=0, sticky='w')
        self.subfam_var = tk.StringVar(value='(Todas)')
        self.subfam_combo = ttk.Combobox(self.control_frame, textvariable=self.subfam_var, state='readonly', width=26)
        self.subfam_combo.grid(row=7, column=0, sticky='ew', pady=(0, 6))
        self.subfam_combo.bind('<<ComboboxSelected>>', lambda *_: self.filter_products())

        # Lote / Ubicacion
        ttk.Label(self.control_frame, text="Lote:").grid(row=8, column=0, sticky='w')
        self.lote_var = tk.StringVar()
        ttk.Entry(self.control_frame, textvariable=self.lote_var, width=28).grid(row=9, column=0, sticky='ew', pady=(0, 6))

        ttk.Label(self.control_frame, text="Ubicacion:").grid(row=10, column=0, sticky='w')
        self.ubi_var = tk.StringVar()
        ttk.Entry(self.control_frame, textvariable=self.ubi_var, width=28).grid(row=11, column=0, sticky='ew', pady=(0, 6))

        # Rango de vencimiento
        ttk.Label(self.control_frame, text="Vencimiento desde (YYYY-MM-DD):").grid(row=12, column=0, sticky='w')
        self.vdesde_var = tk.StringVar()
        ttk.Entry(self.control_frame, textvariable=self.vdesde_var, width=28).grid(row=13, column=0, sticky='ew', pady=(0, 6))
        ttk.Label(self.control_frame, text="Vencimiento hasta (YYYY-MM-DD):").grid(row=14, column=0, sticky='w')
        self.vhasta_var = tk.StringVar()
        ttk.Entry(self.control_frame, textvariable=self.vhasta_var, width=28).grid(row=15, column=0, sticky='ew', pady=(0, 6))

        # Solo con stock
        self.stock_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.control_frame, text='Solo con stock', variable=self.stock_only_var, command=self.filter_products).grid(row=16, column=0, sticky='w', pady=(4, 10))

        # Limpiar filtros
        ttk.Button(self.control_frame, text="Limpiar filtros", command=self._clear_filters, width=26).grid(row=17, column=0, sticky='ew', pady=(2, 2))

        for i in range(0, 18):
            self.control_frame.rowconfigure(i, weight=0)
        self.control_frame.columnconfigure(0, weight=1)

    def _autosize_product_columns(self, event=None):
        try:
            tw = self.product_tree
            tw.update_idletasks()
            width = tw.winfo_width()
            if not width or width < 300:
                return
            specs = [
                ('Producto',    0.45, 220),
                ('Lote',        0.15,  80),
                ('Ubicacion',   0.20, 120),
                ('Vencimiento', 0.12, 100),
                ('Stock',       0.08,  60),
            ]
            for col, frac, minw in specs:
                tw.column(col, width=max(int(width * frac), minw), stretch=True)
        except Exception:
            pass

    def _clear_filters(self) -> None:
        self.search_var.set("")
        self.subfam_var.set('(Todas)')
        self.lote_var.set("")
        self.ubi_var.set("")
        self.vdesde_var.set("")
        self.vhasta_var.set("")
        self.stock_only_var.set(False)
        self.filter_products()

    # -------- Vale / Historial --------
    def _build_vale_and_history(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, padding=(8, 6))
        frame.grid(row=2, column=0, sticky='nsew')
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        self.vale_notebook = ttk.Notebook(frame)
        self.vale_notebook.grid(row=0, column=0, sticky='nsew')

        # Tab Vale
        self.vale_tab = ttk.Frame(self.vale_notebook)
        self.vale_notebook.add(self.vale_tab, text='Vale')
        self.vale_tab.columnconfigure(0, weight=1)
        self.vale_tab.rowconfigure(0, weight=1)

        vale_table_frame = ttk.Frame(self.vale_tab)
        vale_table_frame.grid(row=0, column=0, sticky='nsew')
        vale_table_frame.columnconfigure(0, weight=1)
        vale_table_frame.rowconfigure(1, weight=1)

        self.vale_tree = ttk.Treeview(
            vale_table_frame,
            columns=("Producto", "Lote", "Ubicacion", "Vencimiento", "Cantidad"),
            show='headings',
            selectmode='browse'
        )
        for col, text, w in (
            ('Producto', 'Producto', 380),
            ('Lote', 'Lote', 120),
            ('Ubicacion', 'Ubicacion', 160),
            ('Vencimiento', 'Vencimiento', 130),
            ('Cantidad', 'Cantidad', 100),
        ):
            self.vale_tree.heading(col, text=text)
            self.vale_tree.column(col, width=w, anchor='center' if col != 'Producto' else 'w', stretch=True)

        self.vale_tree.grid(row=0, column=0, sticky='nsew')
        v_vsb = ttk.Scrollbar(vale_table_frame, orient='vertical', command=self.vale_tree.yview)
        v_vsb.grid(row=0, column=1, sticky='ns')
        self.vale_tree.configure(yscrollcommand=v_vsb.set)

        self.vale_actions_frame = ttk.Frame(self.vale_tab, padding=10)
        self.vale_actions_frame.grid(row=0, column=1, sticky='ns', padx=(8, 0))
        ttk.Button(self.vale_actions_frame, text="Eliminar Producto", command=self.remove_from_vale, width=26).pack(pady=6, fill='x')
        ttk.Button(self.vale_actions_frame, text="Generar e Imprimir Vale", command=self.generate_and_print_vale, width=26).pack(pady=6, fill='x')
        ttk.Button(self.vale_actions_frame, text="Limpiar Vale", command=self.clear_vale, width=26).pack(pady=6, fill='x')

        # Tab Historial
        self.hist_tab = ttk.Frame(self.vale_notebook)
        self.vale_notebook.add(self.hist_tab, text='Historial')
        self._build_history_ui()
        self.refresh_history()

        # Tab Manager de Vales
        try:
            self.mgr_tab = ttk.Frame(self.vale_notebook)
            self.vale_notebook.add(self.mgr_tab, text='Manager Vales')
            self._build_manager_ui()
            self.refresh_manager()
        except Exception:
            pass

    def _build_history_ui(self) -> None:
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir, exist_ok=True)

        self.history_frame = ttk.Frame(self.hist_tab, padding=10)
        self.history_frame.pack(fill='both', expand=True)
        self.history_frame.columnconfigure(0, weight=1)
        # Fila 1 (árbol) crecerá
        self.history_frame.rowconfigure(1, weight=1)

        # Barra de búsqueda
        top = ttk.Frame(self.history_frame)
        top.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        ttk.Label(top, text='Buscar:').pack(side='left')
        self.hist_search_var = tk.StringVar(value='')
        hist_entry = ttk.Entry(top, textvariable=self.hist_search_var, width=32)
        hist_entry.pack(side='left', padx=(6, 0))
        self.hist_search_var.trace_add('write', lambda *_: self.refresh_history())

        # Historial basado en el registro: Numero, Estado, Fecha, Archivo, Items
        cols = ("Numero", "Estado", "Fecha", "Archivo", "Items")
        self.history_tree = ttk.Treeview(self.history_frame, columns=cols, show='headings', selectmode='extended')
        self.history_tree.heading('Numero', text='Numero')
        self.history_tree.heading('Estado', text='Estado')
        self.history_tree.heading('Fecha', text='Fecha')
        self.history_tree.heading('Archivo', text='Archivo')
        self.history_tree.heading('Items', text='Items')

        self.history_tree.column('Numero', width=80, anchor='center', stretch=False)
        self.history_tree.column('Estado', width=110, anchor='center', stretch=False)
        self.history_tree.column('Fecha', width=170, anchor='center', stretch=False)
        self.history_tree.column('Archivo', width=520, anchor='w', stretch=True)
        self.history_tree.column('Items', width=80, anchor='center', stretch=False)

        self.history_tree.grid(row=1, column=0, sticky='nsew')
        h_vsb = ttk.Scrollbar(self.history_frame, orient='vertical', command=self.history_tree.yview)
        h_vsb.grid(row=1, column=1, sticky='ns')
        self.history_tree.configure(yscrollcommand=h_vsb.set)
        try:
            self.history_tree.bind('<Configure>', self._autosize_history_columns)
        except Exception:
            pass

        act = ttk.Frame(self.history_frame)
        act.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        ttk.Button(act, text="Unificar seleccionados", command=self.merge_selected_history).pack(side='left', padx=(0, 6))
        ttk.Button(act, text="Abrir PDF", command=self.open_selected_history).pack(side='left', padx=(0, 6))
        ttk.Button(act, text="Reimprimir", command=self.print_selected_history).pack(side='left')

    def refresh_history(self) -> None:
        # Cargar desde el registro; si esta vacio y existen PDFs, reindexar primero
        for i in self.history_tree.get_children():
            self.history_tree.delete(i)
        try:
            rows = self.registry.list()
            if not rows:
                try:
                    if os.path.isdir(self.history_dir) and any(fn.lower().endswith('.pdf') for fn in os.listdir(self.history_dir)):
                        self.registry.reindex()
                        rows = self.registry.list()
                except Exception:
                    pass
            # Filtrar por término de búsqueda si se ingresó
            try:
                term = (self.hist_search_var.get() if hasattr(self, 'hist_search_var') else '').strip().lower()
            except Exception:
                term = ''
            if term:
                def _hit(e):
                    return (
                        term in str(e.get('number', '')).lower() or
                        term in str(e.get('status', '')).lower() or
                        term in str(e.get('created_at', '')).lower() or
                        term in str(e.get('pdf', '')).lower()
                    )
                rows = [e for e in rows if _hit(e)]
            for e in rows:
                iid = str(e.get('number'))
                vals = (e.get('number'), e.get('status'), e.get('created_at'), e.get('pdf'), e.get('items_count'))
                self.history_tree.insert('', 'end', iid=iid, values=vals)
            self._apply_stripes(self.history_tree)
        except Exception:
            pass

    def open_selected_history(self) -> None:
        cur = self.history_tree.focus()
        if not cur:
            messagebox.showwarning("Historial", "Seleccione un vale del listado.")
            return
        try:
            num = int(cur)
            e = self.registry.find_by_number(num)
            if not e:
                messagebox.showwarning("Historial", "No se encontro informacion del vale seleccionado.")
                return
            path = os.path.join(self.history_dir, e.get('pdf', ''))
            if os.path.exists(path):
                os.startfile(path)
        except Exception as e:
            messagebox.showerror("Abrir PDF", f"No se pudo abrir el PDF: {e}")

    def print_selected_history(self) -> None:
        cur = self.history_tree.focus()
        if not cur:
            messagebox.showwarning("Historial", "Seleccione un vale del listado.")
            return
        try:
            num = int(cur)
            e = self.registry.find_by_number(num)
            if not e:
                messagebox.showwarning("Historial", "No se encontro el registro del vale.")
                return
            path = os.path.join(self.history_dir, e.get('pdf', ''))
            if os.path.exists(path) and WINDOWS_OS:
                print_pdf_windows(path, copies=1)
            elif os.path.exists(path):
                os.startfile(path)
        except Exception as e:
            messagebox.showerror("Reimprimir", f"Error al imprimir: {e}")

    def merge_selected_history(self) -> None:
        sels = list(self.history_tree.selection())
        if not sels or len(sels) < 2:
            messagebox.showwarning("Historial", "Seleccione al menos dos vales para unificar.")
            return
        # Resolver rutas desde el registro
        input_paths = []
        for iid in sels:
            try:
                num = int(iid)
            except Exception:
                continue
            e = self.registry.find_by_number(num)
            if not e:
                continue
            p = os.path.join(self.history_dir, e.get('pdf', ''))
            if os.path.exists(p) and p.lower().endswith('.pdf'):
                input_paths.append(p)
        if len(input_paths) < 2:
            messagebox.showwarning("Historial", "No hay suficientes PDFs validos para unificar.")
            return

        # Intentar tabla unificada a partir de sidecars JSON (consolidada)
        unified_rows = []
        missing_json = []
        try:
            import json
        except Exception:
            json = None
        if json is not None:
            acc = {}
            for p in input_paths:
                base, _ = os.path.splitext(p)
                jpath = base + '.json'
                if os.path.exists(jpath):
                    try:
                        with open(jpath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        pdf_name = os.path.basename(p)
                        origin_num = None
                        try:
                            parts = pdf_name.split('_')
                            if len(parts) >= 2 and parts[1].isdigit():
                                origin_num = parts[1].lstrip('0') or '0'
                        except Exception:
                            origin_num = None
                        for it in data.get('items', []):
                            key = (
                                it.get('Producto', ''),
                                it.get('Lote', ''),
                                it.get('Ubicacion', ''),
                                it.get('Vencimiento', ''),
                            )
                            try:
                                qty = int(it.get('Cantidad', 0))
                            except Exception:
                                qty = 0
                            cur = acc.get(key)
                            if not cur:
                                cur = {'Cantidad': 0, 'Origenes': set()}
                                acc[key] = cur
                            cur['Cantidad'] += qty
                            cur['Origenes'].add(str(origin_num) if origin_num is not None else pdf_name)
                    except Exception:
                        missing_json.append(os.path.basename(p))
                else:
                    missing_json.append(os.path.basename(p))
            for (prod, lote, ubi, venc), info in acc.items():
                origenes = sorted(list(info.get('Origenes', [])), key=lambda x: (len(x), x))
                origen_txt = '+'.join(origenes) if origenes else ''
                unified_rows.append({
                    'Origen': origen_txt,
                    'Producto': prod,
                    'Lote': lote,
                    'Ubicacion': ubi,
                    'Vencimiento': venc,
                    'Cantidad': info.get('Cantidad', 0),
                })

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Nombre con origenes destacados (limitado a 5 tokens)
        try:
            origins_in_name = ''
            if unified_rows:
                tokens = []
                for r in unified_rows:
                    o = (r.get('Origen') or '').split('+')
                    for t in o:
                        if t and t not in tokens:
                            tokens.append(t)
                        if len(tokens) >= 5:
                            break
                    if len(tokens) >= 5:
                        break
                if tokens:
                    origins_in_name = '_(' + '+'.join(tokens) + ')'
            out_name = f"vale_unificado{origins_in_name}_{ts}.pdf"
        except Exception:
            out_name = f"vale_unificado_{ts}.pdf"
        out_file = os.path.join(self.history_dir, out_name)

        if unified_rows:
            try:
                from pdf_utils import build_unified_vale_pdf
                build_unified_vale_pdf(out_file, unified_rows, datetime.now())
                self.refresh_history()
                try:
                    os.startfile(out_file)
                except Exception:
                    pass
                if missing_json:
                    messagebox.showinfo('Unificar', 'Se unificaron datos pero faltaron: ' + ', '.join(missing_json))
                return
            except Exception as e:
                messagebox.showwarning('Unificar', f'Fallo al crear tabla unificada ({e}). Se intentara concatenar PDFs...')

        ok, err = self._merge_pdfs(input_paths, out_file)
        if not ok:
            messagebox.showerror("Unificar", f"No se pudo unificar: {err}\nInstale 'pypdf' o 'PyPDF2'.")
            return
        try:
            self.refresh_history()
            os.startfile(out_file)
        except Exception:
            pass

    def _merge_pdfs(self, inputs: list[str], output: str) -> tuple[bool, str | None]:
        """Unifica PDFs con el mejor backend disponible.
        Prioriza pypdf (Merger o PdfMerger) y si falla cae a PyPDF2 o a un Writer/Reader manual.
        """
        try:
            import importlib.util as _iu

            # 1) Intentar con pypdf (varias APIs segun version)
            if _iu.find_spec('pypdf') is not None:
                # a) pypdf exporta PdfMerger
                try:
                    from pypdf import PdfMerger  # type: ignore
                    merger = PdfMerger()
                    for p in inputs:
                        merger.append(p)
                    with open(output, 'wb') as f:
                        merger.write(f)
                    try:
                        merger.close()
                    except Exception:
                        pass
                    return True, None
                except Exception:
                    # b) Algunas versiones exponen Merger en pypdf.merger
                    try:
                        from pypdf.merger import Merger  # type: ignore
                        merger = Merger()
                        for p in inputs:
                            merger.append(p)
                        with open(output, 'wb') as f:
                            merger.write(f)
                        try:
                            merger.close()
                        except Exception:
                            pass
                        return True, None
                    except Exception:
                        # c) Fallback manual con Writer/Reader
                        try:
                            from pypdf import PdfWriter, PdfReader  # type: ignore
                            writer = PdfWriter()
                            for p in inputs:
                                reader = PdfReader(p)
                                for page in getattr(reader, 'pages', []):
                                    writer.add_page(page)
                            with open(output, 'wb') as f:
                                writer.write(f)
                            return True, None
                        except Exception as e3:
                            last_err = e3  # noqa: F841

            # 2) Intentar con PyPDF2
            if _iu.find_spec('PyPDF2') is not None:
                try:
                    from PyPDF2 import PdfMerger  # type: ignore
                    merger = PdfMerger()
                    for p in inputs:
                        merger.append(p)
                    with open(output, 'wb') as f:
                        merger.write(f)
                    try:
                        merger.close()
                    except Exception:
                        pass
                    return True, None
                except Exception:
                    try:
                        from PyPDF2 import PdfWriter, PdfReader  # type: ignore
                        writer = PdfWriter()
                        for p in inputs:
                            reader = PdfReader(p)
                            for page in getattr(reader, 'pages', []):
                                writer.add_page(page)
                        with open(output, 'wb') as f:
                            writer.write(f)
                        return True, None
                    except Exception as e2:
                        return False, f"PyPDF2 fallo: {e2}"

            return False, "No se encontraron modulos 'pypdf' ni 'PyPDF2' en este interprete."
        except Exception as e:
            return False, str(e)

    # -------- Interacciones --------
    def select_inventory_file(self) -> None:
        initialdir = settings.get_last_inventory_dir() or os.getcwd()
        path = filedialog.askopenfilename(
            title='Seleccionar archivo de inventario',
            initialdir=initialdir,
            filetypes=[('Excel', '*.xlsx;*.xls')]
        )
        if not path:
            return
        self.current_file = path
        try:
            base_dir = os.path.dirname(path)
            if base_dir:
                settings.set_last_inventory_dir(base_dir)
            # guarda el ultimo archivo de inventario elegido
            settings.set_last_inventory_file(path)
        except Exception:
            pass
        self._load_inventory(path)

    def _load_inventory(self, path: str) -> None:
        try:
            df = self.manager.load(path, AREA_FILTER)
        except Exception as e:
            messagebox.showerror('Carga de Inventario', f'No se pudo cargar el archivo:\n{e}')
            return
        self.file_label.configure(text=os.path.basename(path))
        # Subfamilias
        try:
            uniq = sorted([x for x in pd.Series(df.get('Subfamilia', [])).dropna().astype(str).unique() if x])
            self.subfam_combo['values'] = ['(Todas)'] + uniq
            self.subfam_combo.set('(Todas)')
        except Exception:
            self.subfam_combo['values'] = ['(Todas)']
            self.subfam_combo.set('(Todas)')

        self.filter_products()

    def filter_products(self) -> None:
        df = self.manager.bioplates_inventory
        if df is None or df.empty:
            self._populate_products(pd.DataFrame())
            return
        opts = FilterOptions(
            producto=self.search_var.get().strip(),
            lote=self.lote_var.get().strip(),
            ubicacion=self.ubi_var.get().strip(),
            venc_desde=self.vdesde_var.get().strip(),
            venc_hasta=self.vhasta_var.get().strip(),
            subfamilia=self.subfam_var.get().strip() or '(Todas)',
            solo_con_stock=bool(self.stock_only_var.get()),
        )
        try:
            out = opts.apply(df)
        except Exception:
            out = df.copy()
        self.filtered_df = out
        self._populate_products(out)

    def _populate_products(self, df: pd.DataFrame) -> None:
        for i in self.product_tree.get_children():
            self.product_tree.delete(i)
        if df is None or df.empty:
            return
        for idx, row in df.iterrows():
            values = [
                row.get('Nombre_del_Producto', ''),
                row.get('Lote', ''),
                row.get('Ubicacion', ''),
                row.get('Vencimiento', ''),
                row.get('Stock', ''),
            ]
            self.product_tree.insert('', 'end', iid=str(int(idx)), values=values)
        self._apply_stripes(self.product_tree)

    def add_to_vale(self) -> None:
        sel = self.product_tree.focus()
        if not sel:
            messagebox.showwarning('Seleccion', 'Seleccione un producto de la tabla.')
            return
        try:
            qty = int(self.quantity_entry.get().strip())
            if qty <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror('Cantidad', 'Ingrese una cantidad valida (> 0).')
            return
        try:
            item_index = int(sel)
            self.manager.add_to_vale(item_index, qty)
        except Exception as e:
            messagebox.showerror('Agregar al Vale', str(e))
            return
        # Refrescar vistas manteniendo filtros
        self.update_vale_treeview()
        self.filter_products()

    def update_vale_treeview(self) -> None:
        for i in self.vale_tree.get_children():
            self.vale_tree.delete(i)
        for i, it in enumerate(self.manager.current_vale):
            self.vale_tree.insert(
                '', 'end', iid=f'val-{i}',
                values=[it.get('Producto',''), it.get('Lote',''), it.get('Ubicacion',''), it.get('Vencimiento',''), it.get('Cantidad','')]
            )
        self._apply_stripes(self.vale_tree)

    def _apply_stripes(self, tree: ttk.Treeview) -> None:
        """Aplica zebra stripes al Treeview para mejorar legibilidad."""
        try:
            tree.tag_configure('evenrow', background='#ffffff')
            tree.tag_configure('oddrow', background='#fafafa')
            for n, iid in enumerate(tree.get_children()):
                tree.item(iid, tags=('evenrow' if n % 2 == 0 else 'oddrow',))
        except Exception:
            pass

    # --------------- Manager de Vales ---------------
    def _build_manager_ui(self) -> None:
        frame = ttk.Frame(self.mgr_tab, padding=10)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Filtros superiores (estado)
        top = ttk.Frame(frame)
        top.grid(row=0, column=0, sticky='ew', pady=(0,6))
        ttk.Label(top, text='Estado:').pack(side='left')
        self.mgr_estado = tk.StringVar(value='(Todos)')
        ttk.Combobox(top, textvariable=self.mgr_estado, values=['(Todos)','Pendiente','Descontado','Anulado'], state='readonly', width=14).pack(side='left', padx=(6,12))
        ttk.Button(top, text='Actualizar', command=self.refresh_manager).pack(side='left')
        ttk.Button(top, text='Reindexar', command=self._mgr_reindex).pack(side='left', padx=(12,0))

        # Búsqueda
        ttk.Label(top, text=' Buscar:').pack(side='left', padx=(12,0))
        self.mgr_search_var = tk.StringVar(value='')
        e_msrch = ttk.Entry(top, textvariable=self.mgr_search_var, width=28)
        e_msrch.pack(side='left', padx=(6,0))
        self.mgr_search_var.trace_add('write', lambda *_: self.refresh_manager())

        cols = ("Numero","Estado","Fecha","Archivo","Items")
        self.mgr_tree = ttk.Treeview(frame, columns=cols, show='headings', selectmode='extended')
        for c, w, anc, st in (
            ('Numero', 80, 'center', False),
            ('Estado', 110, 'center', False),
            ('Fecha', 170, 'center', False),
            ('Archivo', 520, 'w', True),
            ('Items', 80, 'center', False),
        ):
            self.mgr_tree.heading(c, text=c)
            self.mgr_tree.column(c, width=w, anchor=anc, stretch=st)
        self.mgr_tree.grid(row=1, column=0, sticky='nsew')
        vbar = ttk.Scrollbar(frame, orient='vertical', command=self.mgr_tree.yview)
        vbar.grid(row=1, column=1, sticky='ns')
        self.mgr_tree.configure(yscrollcommand=vbar.set)

        # Acciones
        act = ttk.Frame(frame)
        act.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8,0))
        ttk.Button(act, text='Marcar Pendiente', command=lambda: self._mgr_set_status('Pendiente')).pack(side='left', padx=(0,6))
        ttk.Button(act, text='Marcar Descontado', command=lambda: self._mgr_set_status('Descontado')).pack(side='left', padx=(0,6))
        ttk.Button(act, text='Marcar Anulado', command=lambda: self._mgr_set_status('Anulado')).pack(side='left', padx=(0,6))
        ttk.Button(act, text='Listado PDF (Pendientes)', command=lambda: self._mgr_export_pdf('Pendiente')).pack(side='right', padx=(6,0))
        ttk.Button(act, text='Listado PDF (Descontados)', command=lambda: self._mgr_export_pdf('Descontado')).pack(side='right', padx=(6,0))
        ttk.Button(act, text='Exportar Excel (Pendientes)', command=lambda: self._mgr_export_excel('Pendiente')).pack(side='right', padx=(6,0))
        ttk.Button(act, text='Exportar Excel (Descontados)', command=lambda: self._mgr_export_excel('Descontado')).pack(side='right', padx=(6,0))

    def refresh_manager(self) -> None:
        try:
            for i in self.mgr_tree.get_children():
                self.mgr_tree.delete(i)
            estado = self.mgr_estado.get() if hasattr(self, 'mgr_estado') else '(Todos)'
            entries = self.registry.list(None if estado in (None,'', '(Todos)') else estado)
            if not entries:
                try:
                    if os.path.isdir(self.history_dir) and any(fn.lower().endswith('.pdf') for fn in os.listdir(self.history_dir)):
                        self.registry.reindex()
                        entries = self.registry.list(None if estado in (None,'', '(Todos)') else estado)
                except Exception:
                    pass
            # Filtrar por búsqueda
            try:
                term = (self.mgr_search_var.get() if hasattr(self, 'mgr_search_var') else '').strip().lower()
            except Exception:
                term = ''
            if term:
                def _hit(e):
                    return (
                        term in str(e.get('number', '')).lower() or
                        term in str(e.get('status', '')).lower() or
                        term in str(e.get('created_at', '')).lower() or
                        term in str(e.get('pdf', '')).lower()
                    )
                entries = [e for e in entries if _hit(e)]
            for e in entries:
                self.mgr_tree.insert('', 'end', iid=str(e.get('number')), values=(e.get('number'), e.get('status'), e.get('created_at'), e.get('pdf'), e.get('items_count')))
            self._apply_stripes(self.mgr_tree)
        except Exception:
            pass


    def _autosize_history_columns(self, event=None) -> None:
        """Ajusta columnas del Historial para evitar espacios en blanco."""
        try:
            tw = self.history_tree
            tw.update_idletasks()
            width = tw.winfo_width()
            if not width:
                return
            fecha_min = 180
            fecha_w = max(fecha_min, int(width * 0.22))
            archivo_w = max(200, width - fecha_w - 20)
            tw.column('Archivo', width=archivo_w, anchor='w', stretch=True)
            tw.column('Fecha', width=fecha_w, anchor='center', stretch=False)
        except Exception:
            pass

    def _mgr_reindex(self) -> None:
        try:
            res = self.registry.reindex()
            self.refresh_manager()
            self.refresh_history()
            try:
                messagebox.showinfo('Reindexar', f"Agregados: {res.get('added',0)}\nOmitidos: {res.get('skipped',0)}")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror('Reindexar', f'No se pudo reindexar: {e}')
    def _mgr_selected_numbers(self) -> list[int]:
        try:
            return [int(i) for i in self.mgr_tree.selection()]
        except Exception:
            return []

    def _mgr_set_status(self, new_status: str) -> None:
        nums = self._mgr_selected_numbers()
        if not nums:
            messagebox.showwarning('Manager Vales', 'Seleccione uno o mas vales.')
            return
        try:
            changed = self.registry.update_status(nums, new_status)
            if changed:
                self.refresh_manager()
                self.refresh_history()
        except Exception as e:
            messagebox.showerror('Manager Vales', f'No se pudo actualizar el estado: {e}')

    def _mgr_export_excel(self, status: str) -> None:
        try:
            rows = self.registry.list(status)
            if not rows:
                messagebox.showinfo('Exportar', f'No hay vales con estado {status}.')
                return
            import pandas as _pd
            df = _pd.DataFrame(rows)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            out = os.path.join(self.history_dir, f'vales_{status.lower()}_{ts}.xlsx')
            df.to_excel(out, index=False)
            try:
                os.startfile(out)
            except Exception:
                pass
            messagebox.showinfo('Exportar', f'Listado exportado: {os.path.basename(out)}')
        except Exception as e:
            messagebox.showerror('Exportar', f'Error al exportar: {e}')

    def _mgr_export_pdf(self, status: str) -> None:
        try:
            rows = self.registry.list(status)
            if not rows:
                messagebox.showinfo('Listado', f'No hay vales con estado {status}.')
                return
            from pdf_utils import build_vales_list_pdf
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            title = f"Listado de vales - {status}"
            out = os.path.join(self.history_dir, f'listado_vales_{status.lower()}_{ts}.pdf')
            build_vales_list_pdf(out, title, rows)
            try:
                os.startfile(out)
            except Exception:
                pass
            messagebox.showinfo('Listado', f'PDF generado: {os.path.basename(out)}')
        except Exception as e:
            messagebox.showerror('Listado', f'Error al generar PDF: {e}')

    def remove_from_vale(self) -> None:
        sel = self.vale_tree.focus()
        if not sel or not sel.startswith('val-'):
            messagebox.showwarning('Vale', 'Seleccione un item del vale.')
            return
        try:
            idx = int(sel.split('-')[1])
            self.manager.remove_from_vale(idx)
        except Exception as e:
            messagebox.showerror('Eliminar', str(e))
            return
        self.update_vale_treeview()
        self.filter_products()

    def clear_vale(self) -> None:
        self.manager.clear_vale()
        self.update_vale_treeview()
        self.filter_products()

    def generate_and_print_vale(self) -> None:
        if not self.manager.current_vale:
            messagebox.showwarning('Vale', 'No hay productos en el vale.')
            return
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Reservar numero para nombrar el archivo
        try:
            number = self.registry.next_number()
        except Exception:
            number = None
        if number is not None:
            padded = f"{int(number):06d}"
            base_pdf = f"vale_{padded}_{ts}.pdf"
            base_json = f"vale_{padded}_{ts}.json"
        else:
            base_pdf = f"vale_{ts}.pdf"
            base_json = f"vale_{ts}.json"
        filename = os.path.join(self.history_dir, base_pdf)
        try:
            # Generar PDF (via ValeManager -> pdf_utils)
            self.manager.generate_pdf(filename, datetime.now())
            # Guardar datos estructurados del vale (sidecar JSON)
            try:
                import json
                sidecar = os.path.join(self.history_dir, base_json)
                payload = {
                    'filename': os.path.basename(filename),
                    'emission_time': datetime.now().isoformat(timespec='seconds'),
                    'items': self.manager.current_vale,
                }
                with open(sidecar, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                sidecar = ''
            # Impresion automatica si esta habilitada
            if WINDOWS_OS and settings.get_auto_print():
                print_pdf_windows(filename, copies=1)
            # Abrir para vista previa
            try:
                os.startfile(filename)
            except Exception:
                pass
            messagebox.showinfo('Vale Generado', 'Vale generado correctamente.')
            # Registrar en el indice con el numero reservado y refrescar vistas
            try:
                if number is not None:
                    self.registry.register_with_number(
                        int(number),
                        os.path.basename(filename),
                        os.path.basename(sidecar) if sidecar else '',
                        len(self.manager.current_vale),
                    )
            except Exception:
                pass
            # Limpiar vale e historial
            self.manager.current_vale = []
            self.update_vale_treeview()
            self.refresh_history()
            try:
                self.refresh_manager()
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror('Generar Vale', f'Ocurrio un error: {e}')


def run_app() -> None:
    root = tk.Tk()
    _ = ValeConsumoApp(root)
    root.mainloop()


if __name__ == '__main__':
    run_app()


