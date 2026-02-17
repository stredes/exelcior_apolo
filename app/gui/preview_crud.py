# app/gui/preview_crud.py
# -*- coding: utf-8 -*-
"""
Preview CRUD: módulo único que provee
- PreviewCRUDFrame: widget CRUD reutilizable sobre un pandas.DataFrame (agregar/editar/eliminar/deshacer/guardar)
- open_preview_crud: función que crea la ventana Toplevel de Vista Previa con botón Imprimir y monta el widget

Uso desde main_app.py:
    from app.gui.preview_crud import open_preview_crud
    open_preview_crud(self, self.transformed_df, self.mode, on_print=self._threaded_print)
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import pandas as pd


# ================== Widget CRUD ==================
class PreviewCRUDFrame(ttk.Frame):
    def __init__(
        self,
        master,
        df: pd.DataFrame,
        total_cols: list[str] | None = None,
        on_change=None,         # callback(df) cada vez que cambia (Guardar, editar, eliminar, agregar)
        title: str | None = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self._df: pd.DataFrame = df.copy(deep=True) if df is not None else pd.DataFrame()
        self._undo_stack: list[pd.DataFrame] = []
        self._total_cols = total_cols or []
        self._on_change = on_change

        # ---------- Toolbar ----------
        toolbar = ttk.Frame(self, padding=(0, 6))
        toolbar.pack(fill=tk.X, side=tk.TOP)

        if title:
            ttk.Label(toolbar, text=title, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(toolbar, text="Agregar", command=self._add_row_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Editar", command=self._open_edit_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Eliminar", command=self._delete_selected_rows).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Deshacer", command=self._undo_last).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Guardar", command=self._emit_change).pack(side=tk.LEFT, padx=12)

        self._info_lbl = ttk.Label(toolbar, text="")
        self._info_lbl.pack(side=tk.RIGHT, padx=6)

        # ---------- Tabla ----------
        table_frame = ttk.Frame(self, padding=(0, 0))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self._tv = ttk.Treeview(table_frame, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tv.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self._tv.xview)
        self._tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        try:
            import tkinter.font as tkfont
            self._tv_font = tkfont.nametofont("TkDefaultFont")
        except Exception:
            import tkinter.font as tkfont
            self._tv_font = tkfont.Font()

        self._setup_columns()
        self.refresh()

    # ---------------- API pública ----------------

    def get_dataframe(self) -> pd.DataFrame:
        return self._df.copy(deep=True)

    # reserved: permite refrescar la grilla sin recrear la ventana de preview
    def set_dataframe(self, df: pd.DataFrame):
        self._push_undo()
        self._df = df.copy(deep=True) if df is not None else pd.DataFrame()
        self._setup_columns()
        self.refresh()

    def refresh(self):
        self._fill_rows()
        self._auto_widths()
        self._update_totals_label()

    # ---------------- Internos ----------------

    def _setup_columns(self):
        cols = list(self._df.columns) if not self._df.empty else []
        self._tv["columns"] = cols
        for c in self._tv["columns"]:
            self._tv.heading(c, text=c)
            self._tv.column(c, width=120, anchor=tk.CENTER)

    def _fill_rows(self):
        for item in self._tv.get_children():
            self._tv.delete(item)
        if self._df.empty:
            self._info_lbl.configure(text="Sin datos")
            return
        for idx, row in self._df.iterrows():
            values = [row.get(c, "") for c in self._df.columns]
            self._tv.insert("", "end", iid=str(idx), values=values)

    def _auto_widths(self):
        if self._df.empty:
            return
        MAX_W, MIN_W, PAD = 380, 90, 24
        sample = self._df.head(150)
        for col in self._df.columns:
            muestras = [str(col)] + [str(v) for v in sample[col].tolist()]
            try:
                ancho = max((self._tv_font.measure(s) for s in muestras), default=MIN_W) + PAD
            except Exception:
                ancho = 120
            ancho = max(MIN_W, min(ancho, MAX_W))
            self._tv.column(col, width=ancho, anchor=tk.CENTER)

    def _update_totals_label(self):
        if self._df is None or self._df.empty:
            self._info_lbl.configure(text="Sin datos")
            return
        parts = [f"Filas: {len(self._df):,}"]
        for c in self._total_cols:
            if c in self._df.columns:
                try:
                    total = int(pd.to_numeric(self._df[c], errors="coerce").fillna(0).sum())
                    parts.append(f"Total {c}: {total}")
                except Exception:
                    pass
        self._info_lbl.configure(text=" | ".join(parts))

    def _push_undo(self):
        try:
            self._undo_stack.append(self._df.copy(deep=True))
            if len(self._undo_stack) > 12:
                self._undo_stack.pop(0)
        except Exception:
            pass

    def _undo_last(self):
        if self._undo_stack:
            self._df = self._undo_stack.pop()
            self.refresh()

    def _emit_change(self):
        if callable(self._on_change):
            try:
                self._on_change(self.get_dataframe())
            except Exception:
                pass
        self._update_totals_label()

    def _open_edit_dialog(self):
        sel = self._tv.selection()
        if not sel:
            self._toast("Selecciona una fila para editar.")
            return
        iid = sel[0]
        try:
            idx = self._df.index[self._df.index.astype(str) == iid][0]
        except Exception:
            self._toast("No se pudo mapear la fila seleccionada.")
            return

        row = self._df.loc[idx]
        cols = list(self._df.columns)

        win = tk.Toplevel(self)
        win.title("Editar fila")
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        entries = {}
        for i, c in enumerate(cols):
            ttk.Label(frm, text=c).grid(row=i, column=0, sticky="w", padx=6, pady=3)
            e = ttk.Entry(frm, width=52)
            e.insert(0, "" if pd.isna(row.get(c)) else str(row.get(c)))
            e.grid(row=i, column=1, sticky="ew", padx=6, pady=3)
            entries[c] = e
        frm.grid_columnconfigure(1, weight=1)

        def guardar():
            self._push_undo()
            for c in cols:
                self._df.loc[idx, c] = entries[c].get()
            win.destroy()
            self.refresh()
            self._emit_change()

        ttk.Button(frm, text="Guardar", command=guardar).grid(row=len(cols), column=0, padx=6, pady=10)
        ttk.Button(frm, text="Cancelar", command=win.destroy).grid(row=len(cols), column=1, padx=6, pady=10, sticky="e")

    def _delete_selected_rows(self):
        sel = self._tv.selection()
        if not sel:
            self._toast("Selecciona una o más filas para eliminar.")
            return
        idx_list = []
        for iid in sel:
            try:
                idx = self._df.index[self._df.index.astype(str) == iid][0]
                idx_list.append(idx)
            except Exception:
                pass
        if not idx_list:
            self._toast("No se pudieron mapear las filas seleccionadas.")
            return
        self._push_undo()
        self._df = self._df.drop(index=idx_list, errors="ignore")
        self.refresh()
        self._emit_change()

    def _add_row_dialog(self):
        cols = list(self._df.columns) if not self._df.empty else []

        win = tk.Toplevel(self)
        win.title("Agregar fila")
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        entries = {}
        if cols:
            for i, c in enumerate(cols):
                ttk.Label(frm, text=c).grid(row=i, column=0, sticky="w", padx=6, pady=3)
                e = ttk.Entry(frm, width=52)
                e.grid(row=i, column=1, sticky="ew", padx=6, pady=3)
                entries[c] = e
            frm.grid_columnconfigure(1, weight=1)
        else:
            ttk.Label(frm, text="No hay columnas. Cargue un DataFrame con columnas.").pack()

        def agregar():
            if not cols:
                win.destroy()
                return
            self._push_undo()
            data = {c: entries[c].get() for c in cols}
            new_row = pd.DataFrame([data])
            self._df = pd.concat([self._df, new_row], ignore_index=False)
            win.destroy()
            self.refresh()
            self._emit_change()

        ttk.Button(frm, text="Agregar", command=agregar).grid(row=len(cols), column=0, padx=6, pady=10)
        ttk.Button(frm, text="Cancelar", command=win.destroy).grid(row=len(cols), column=1, padx=6, pady=10, sticky="e")

    def _toast(self, msg: str):
        self._info_lbl.configure(text=msg)
        self.after(2200, self._update_totals_label)


# ================== Ventana (Preview + CRUD) ==================
def open_preview_crud(
    parent_app,
    df: pd.DataFrame,
    mode: str,
    on_print,                 # callback sin args para imprimir
    on_df_change=None,        # callback(df) cuando el DF cambia
) -> tk.Toplevel:
    """
    Crea la ventana Toplevel con:
      - Título con modo
      - Botón Imprimir
      - PreviewCRUDFrame (CRUD + totales)
    Se encarga de sincronizar parent_app.transformed_df al editar/guardar.
    """
    # Cierra la anterior si existe
    try:
        if getattr(parent_app, "_preview_win", None) is not None and parent_app._preview_win.winfo_exists():
            parent_app._preview_win.destroy()
    except Exception:
        pass

    vista = tk.Toplevel(parent_app)
    parent_app._preview_win = vista
    vista.title("Vista Previa")
    vista.geometry("1100x700")
    vista.configure(bg="#F9FAFB")

    # Top bar con título y botón imprimir
    topbar = ttk.Frame(vista, padding=(10, 8))
    topbar.pack(fill=tk.X, side=tk.TOP)
    ttk.Label(topbar, text=f"Modo: {mode.capitalize()}", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
    ttk.Button(topbar, text="Imprimir", command=on_print).pack(side=tk.RIGHT)

    # Totales por modo (FedEx: BULTOS)
    total_cols = ["BULTOS"] if (mode or "").strip().lower() == "fedex" else []

    def _on_change(df_actual: pd.DataFrame):
        # sincroniza el DF activo para que imprima lo que se ve
        try:
            parent_app.transformed_df = df_actual
        except Exception:
            pass
        if callable(on_df_change):
            try:
                on_df_change(df_actual)
            except Exception:
                pass

    crud = PreviewCRUDFrame(
        vista,
        df=df,
        total_cols=total_cols,
        on_change=_on_change,
        padding=10
    )
    crud.pack(fill=tk.BOTH, expand=True)

    return vista
