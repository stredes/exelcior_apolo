# app/gui/preview_crud.py
# -*- coding: utf-8 -*-
"""
Preview CRUD: módulo único que provee
- PreviewCRUDFrame: widget CRUD reutilizable sobre un pandas.DataFrame
- open_preview_crud: función que crea la ventana Toplevel de Vista Previa
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd


class PreviewCRUDFrame(ttk.Frame):
    def __init__(
        self,
        master,
        df: pd.DataFrame,
        total_cols: list[str] | None = None,
        on_change=None,
        title: str | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._df: pd.DataFrame = df.copy(deep=True) if df is not None else pd.DataFrame()
        self._undo_stack: list[pd.DataFrame] = []
        self._total_cols = total_cols or []
        self._on_change = on_change
        self._filter_var = tk.StringVar(value="")

        self._configure_styles()

        shell = tk.Frame(self, bg="#EEF4F8")
        shell.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(shell, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D8E4EF")
        header.pack(fill=tk.X, padx=10, pady=(10, 8))

        header_left = tk.Frame(header, bg="#FFFFFF")
        header_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=14)
        if title:
            ttk.Label(header_left, text=title, style="PreviewTitle.TLabel").pack(anchor="w")
        ttk.Label(
            header_left,
            text="Revisa, filtra y corrige filas antes de imprimir. Lo que guardes aqui sera la salida final.",
            style="PreviewSub.TLabel",
        ).pack(anchor="w", pady=(4, 10))

        filter_row = tk.Frame(header_left, bg="#FFFFFF")
        filter_row.pack(fill=tk.X)
        ttk.Label(filter_row, text="Filtro rapido", style="PreviewMeta.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        filter_entry = ttk.Entry(filter_row, textvariable=self._filter_var, width=30)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        filter_entry.bind("<KeyRelease>", lambda _e: self.refresh())
        ttk.Button(filter_row, text="Limpiar", style="PreviewGhost.TButton", command=self._clear_filter).pack(side=tk.LEFT, padx=(8, 0))

        header_right = tk.Frame(header, bg="#FFFFFF")
        header_right.pack(side=tk.RIGHT, padx=16, pady=14)

        self._info_lbl = ttk.Label(header_right, text="", style="PreviewStat.TLabel", justify="right")
        self._info_lbl.pack(anchor="e", pady=(0, 10))

        actions = ttk.Frame(header_right)
        actions.pack(anchor="e")
        ttk.Button(actions, text="Agregar", style="PreviewAction.TButton", command=self._add_row_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="Editar", style="PreviewAction.TButton", command=self._open_edit_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="Eliminar", style="PreviewAction.TButton", command=self._delete_selected_rows).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="Deshacer", style="PreviewGhost.TButton", command=self._undo_last).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="Guardar cambios", style="PreviewPrimary.TButton", command=self._emit_change).pack(side=tk.LEFT, padx=(8, 0))

        table_shell = tk.Frame(shell, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D8E4EF")
        table_shell.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        table_frame = ttk.Frame(table_shell, padding=(10, 10, 10, 6))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self._tv = ttk.Treeview(table_frame, show="headings", selectmode="extended", style="Preview.Treeview")
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

        self._tv.tag_configure("even", background="#F7FAFD")
        self._tv.tag_configure("odd", background="#EEF4FA")

        self._setup_columns()
        self.refresh()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.configure("PreviewTitle.TLabel", font=("Segoe UI Semibold", 14), foreground="#14324B", background="#FFFFFF")
        style.configure("PreviewSub.TLabel", font=("Segoe UI", 9), foreground="#627D98", background="#FFFFFF")
        style.configure("PreviewMeta.TLabel", font=("Segoe UI Semibold", 8), foreground="#486581", background="#FFFFFF")
        style.configure("PreviewStat.TLabel", font=("Segoe UI Semibold", 9), foreground="#0F4C81", background="#FFFFFF")
        style.configure("PreviewAction.TButton", font=("Segoe UI Semibold", 9), padding=(10, 7))
        style.configure("PreviewGhost.TButton", font=("Segoe UI Semibold", 9), padding=(10, 7))
        style.configure("PreviewPrimary.TButton", font=("Segoe UI Semibold", 9), padding=(12, 7))
        style.configure("Preview.Treeview", rowheight=28, font=("Segoe UI", 9), background="#F7FAFD", fieldbackground="#F7FAFD")
        style.configure("Preview.Treeview.Heading", font=("Segoe UI Semibold", 9))

    def get_dataframe(self) -> pd.DataFrame:
        return self._df.copy(deep=True)

    def set_dataframe(self, df: pd.DataFrame):
        self._push_undo()
        self._df = df.copy(deep=True) if df is not None else pd.DataFrame()
        self._setup_columns()
        self.refresh()

    def refresh(self):
        self._fill_rows()
        self._auto_widths()
        self._update_totals_label()

    def _clear_filter(self):
        self._filter_var.set("")
        self.refresh()

    def _visible_df(self) -> pd.DataFrame:
        if self._df.empty:
            return self._df

        query = (self._filter_var.get() or "").strip().lower()
        if not query:
            return self._df

        mask = self._df.astype(str).apply(
            lambda col: col.str.lower().str.contains(query, na=False)
        ).any(axis=1)
        return self._df.loc[mask]

    def _setup_columns(self):
        cols = list(self._df.columns) if not self._df.empty else []
        self._tv["columns"] = cols
        for c in cols:
            self._tv.heading(c, text=c)
            self._tv.column(c, width=120, anchor=tk.CENTER)

    def _fill_rows(self):
        for item in self._tv.get_children():
            self._tv.delete(item)

        if self._df.empty:
            self._info_lbl.configure(text="Sin datos")
            return

        visible_df = self._visible_df()
        if visible_df.empty:
            self._info_lbl.configure(text="Sin coincidencias")
            return

        for pos, (idx, row) in enumerate(visible_df.iterrows()):
            values = [row.get(c, "") for c in self._df.columns]
            tag = "even" if pos % 2 == 0 else "odd"
            self._tv.insert("", "end", iid=str(idx), values=values, tags=(tag,))

    def _auto_widths(self):
        visible_df = self._visible_df()
        if visible_df.empty:
            return

        max_w, min_w, pad = 380, 90, 24
        sample = visible_df.head(150)
        for col in self._df.columns:
            muestras = [str(col)] + [str(v) for v in sample[col].tolist()]
            try:
                ancho = max((self._tv_font.measure(s) for s in muestras), default=min_w) + pad
            except Exception:
                ancho = 120
            ancho = max(min_w, min(ancho, max_w))
            self._tv.column(col, width=ancho, anchor=tk.CENTER)

    def _update_totals_label(self):
        if self._df is None or self._df.empty:
            self._info_lbl.configure(text="Sin datos")
            return

        visible_df = self._visible_df()
        parts = [f"{len(visible_df):,} visibles"]
        if len(visible_df) != len(self._df):
            parts.append(f"{len(self._df):,} totales")
        for c in self._total_cols:
            if c in visible_df.columns:
                try:
                    total = int(pd.to_numeric(visible_df[c], errors="coerce").fillna(0).sum())
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
        self._toast("Cambios guardados en la vista previa.")

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
        win.configure(bg="#F6FAFD")
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        entries = {}
        for i, c in enumerate(cols):
            ttk.Label(frm, text=c).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            e = ttk.Entry(frm, width=52)
            e.insert(0, "" if pd.isna(row.get(c)) else str(row.get(c)))
            e.grid(row=i, column=1, sticky="ew", padx=6, pady=4)
            entries[c] = e
        frm.grid_columnconfigure(1, weight=1)

        def guardar():
            self._push_undo()
            for c in cols:
                self._df.loc[idx, c] = entries[c].get()
            win.destroy()
            self.refresh()
            self._emit_change()

        ttk.Button(frm, text="Guardar", command=guardar).grid(row=len(cols), column=0, padx=6, pady=12)
        ttk.Button(frm, text="Cancelar", command=win.destroy).grid(row=len(cols), column=1, padx=6, pady=12, sticky="e")

    def _delete_selected_rows(self):
        sel = self._tv.selection()
        if not sel:
            self._toast("Selecciona una o mas filas para eliminar.")
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
        win.configure(bg="#F6FAFD")
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        entries = {}
        if cols:
            for i, c in enumerate(cols):
                ttk.Label(frm, text=c).grid(row=i, column=0, sticky="w", padx=6, pady=4)
                e = ttk.Entry(frm, width=52)
                e.grid(row=i, column=1, sticky="ew", padx=6, pady=4)
                entries[c] = e
            frm.grid_columnconfigure(1, weight=1)
        else:
            ttk.Label(frm, text="No hay columnas disponibles para agregar filas.").pack()

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

        ttk.Button(frm, text="Agregar", command=agregar).grid(row=len(cols), column=0, padx=6, pady=12)
        ttk.Button(frm, text="Cancelar", command=win.destroy).grid(row=len(cols), column=1, padx=6, pady=12, sticky="e")

    def _toast(self, msg: str):
        self._info_lbl.configure(text=msg)
        self.after(2200, self._update_totals_label)


def open_preview_crud(
    parent_app,
    df: pd.DataFrame,
    mode: str,
    on_print,
    on_df_change=None,
) -> tk.Toplevel:
    try:
        if getattr(parent_app, "_preview_win", None) is not None and parent_app._preview_win.winfo_exists():
            parent_app._preview_win.destroy()
    except Exception:
        pass

    vista = tk.Toplevel(parent_app)
    parent_app._preview_win = vista
    vista.title("Vista Previa")
    vista.geometry("1180x760")
    vista.configure(bg="#EEF4F8")

    top_shell = tk.Frame(vista, bg="#EEF4F8")
    top_shell.pack(fill=tk.X, padx=12, pady=(12, 8))

    hero = tk.Frame(top_shell, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D8E4EF")
    hero.pack(fill=tk.X)

    hero_left = tk.Frame(hero, bg="#FFFFFF")
    hero_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=14)
    tk.Label(
        hero_left,
        text=f"Vista Previa de {mode.capitalize()}",
        bg="#FFFFFF",
        fg="#102A43",
        font=("Segoe UI Semibold", 16),
    ).pack(anchor="w")
    tk.Label(
        hero_left,
        text="Revisa el contenido final antes de imprimir. Cualquier cambio que hagas aqui se usa como fuente de impresion.",
        bg="#FFFFFF",
        fg="#627D98",
        font=("Segoe UI", 9),
        wraplength=720,
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    hero_right = tk.Frame(hero, bg="#FFFFFF")
    hero_right.pack(side=tk.RIGHT, padx=16, pady=14)
    tk.Label(
        hero_right,
        text=f"{len(df) if df is not None else 0:,} filas",
        bg="#EAF4FF",
        fg="#0F4C81",
        font=("Segoe UI Semibold", 10),
        padx=12,
        pady=8,
    ).pack(anchor="e", pady=(0, 8))
    ttk.Button(hero_right, text="Imprimir ahora", command=on_print).pack(anchor="e")

    total_cols = ["BULTOS"] if (mode or "").strip().lower() == "fedex" else []

    def _on_change(df_actual: pd.DataFrame):
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
        title="Editor de datos previo a impresion",
        padding=0,
    )
    crud.pack(fill=tk.BOTH, expand=True)

    return vista
