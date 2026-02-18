# app/gui/buscador_codigos_postales.py
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
from typing import Dict, Iterable, Optional
from functools import partial

from app.core.logger_eventos import capturar_log_bod1
# utils expone load_config y guardar_ultimo_path
from app.utils.utils import guardar_ultimo_path, load_config as load_config_from_file


class BuscadorCodigosPostales(tk.Toplevel):
    """
    Ventana de búsqueda de códigos postales por comuna o región.

    - Caso preferente: encabezados en FILA 2 (index=1) con columnas A:D.
      (Comuna/Localidad | Provincia | Region | Codigo Postal)
    - Si falla, se prueban otros headers/estrategias (header=2, header=0..5, sin encabezado, inferencia).
    - Normaliza a: REGIÓN, COMUNA, CÓDIGO POSTAL.
    - Búsqueda sin acentos y sin mayúsculas (debounce).
    - Copia por doble clic, botón o Ctrl+C.
    """

    CONFIG_KEY_FILE = "archivo_codigos_postales"

    COLS_TARGET = ("REGIÓN", "COMUNA", "CÓDIGO POSTAL")

    # Sinónimos aceptados (normalizados a minúsculas sin acentos)
    COL_SYNONYMS: Dict[str, str] = {
        # Región
        "region": "REGIÓN",
        "región": "REGIÓN",
        "regi\u00f3n": "REGIÓN",
        # Comuna / Localidad
        "comuna": "COMUNA",
        "comuna/localidad": "COMUNA",
        "localidad": "COMUNA",
        # Código Postal
        "codigo postal": "CÓDIGO POSTAL",
        "código postal": "CÓDIGO POSTAL",
        "c\u00f3digo postal": "CÓDIGO POSTAL",
        "cod postal": "CÓDIGO POSTAL",
        "codigo ubigeo": "CÓDIGO POSTAL",
        "ubigeo": "CÓDIGO POSTAL",
        "cp": "CÓDIGO POSTAL",
    }

    # Orden de headers preferidos
    PREFERRED_HEADER_ROWS = [1, 2, 0, 3, 4, 5]

    @staticmethod
    def _excel_engine_for_path(path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".ods":
            return "odf"
        if ext == ".xls":
            return "xlrd"
        return "openpyxl"

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("Buscador de Códigos Postales")
        self.geometry("900x560")
        self.config(bg="#F9FAFB")
        self.minsize(780, 480)

        # Estado
        self.df: pd.DataFrame = pd.DataFrame()
        self._ruta_excel: Optional[str] = None
        self._search_after_id: Optional[str] = None
        self._creating = True

        # UI
        self._build_header()
        self._build_toolbar()
        self._build_tree()
        self._build_statusbar()

        # Atajos
        self.bind("<Control-f>", lambda e: self.entry_busqueda.focus_set())
        self.bind("<Control-F>", lambda e: self.entry_busqueda.focus_set())
        self.bind("<Return>", lambda e: self._buscar_now())
        self.bind("<Escape>", lambda e: self._clear_search())
        self.bind("<Control-c>", self._copiar_codigo_postal)

        # Cargar ruta y datos
        self.after(50, self._resolver_ruta_y_cargar)

    # --------------------------- Construcción de UI ---------------------------

    def _build_header(self) -> None:
        header = tk.Frame(self, bg="#F9FAFB")
        header.pack(fill="x", padx=14, pady=(12, 4))

        tk.Label(
            header,
            text="Buscador de Códigos Postales",
            bg="#F9FAFB",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        self.lbl_archivo = tk.Label(
            header,
            text="Archivo: (no cargado)",
            bg="#F9FAFB",
            fg="#555",
            font=("Segoe UI", 9, "italic")
        )
        self.lbl_archivo.pack(side="right")

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg="#F9FAFB")
        bar.pack(fill="x", padx=14, pady=(2, 8))

        tk.Label(bar, text="Buscar comuna o región:", bg="#F9FAFB", font=("Segoe UI", 10)).pack(side="left")

        self.entry_busqueda = tk.Entry(bar, width=40)
        self.entry_busqueda.pack(side="left", padx=8)
        self.entry_busqueda.bind("<KeyRelease>", self._on_search_changed)

        ttk.Button(bar, text="Buscar", command=self._buscar_now).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Limpiar", command=self._clear_search).pack(side="left")

        tk.Frame(bar, bg="#F9FAFB").pack(side="left", expand=True, fill="x")
        ttk.Button(bar, text="Cambiar archivo…", command=self._cambiar_archivo).pack(side="right")

    def _build_tree(self) -> None:
        frame = tk.Frame(self, bg="#F9FAFB")
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        cols = self.COLS_TARGET
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center", width=180, stretch=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._copiar_codigo_postal)

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg="#EEF2F7")
        bar.pack(fill="x", side="bottom")

        self.lbl_estado = tk.Label(bar, text="Listo", bg="#EEF2F7", fg="#333", anchor="w")
        self.lbl_estado.pack(side="left", padx=8, pady=3)

        self.btn_copiar = ttk.Button(bar, text="Copiar Código Postal", command=self._copiar_codigo_postal)
        self.btn_copiar.pack(side="right", padx=8, pady=3)
        self.btn_copiar["state"] = "disabled"

    # ---------------------------- Flujo de carga -----------------------------

    def _resolver_ruta_y_cargar(self) -> None:
        """
        Comportamiento solicitado:
        - Si hay ruta guardada y el archivo existe -> cargar sin preguntar.
        - Si hay ruta guardada pero el archivo ya no existe -> NO abrir diálogo; mostrar aviso
          y permitir que el usuario use “Cambiar archivo…”.
        - Si no hay ruta guardada (primera vez) -> abrir diálogo y guardar la elección.
        """
        cfg = load_config_from_file() or {}
        ruta = cfg.get(self.CONFIG_KEY_FILE)

        # Caso 1: tenemos ruta válida -> cargar sin preguntar
        if ruta and Path(ruta).exists():
            self._usar_ruta_y_cargar(ruta)
            return

        # Caso 2: ruta guardada pero ya no existe -> NO abrir diálogo (dejar al usuario)
        if ruta and not Path(ruta).exists():
            capturar_log_bod1(f"[CP] Ruta guardada no existe: {ruta}", "warning")
            self._ruta_excel = None
            self.lbl_archivo.config(
                text="Archivo: (no encontrado; use «Cambiar archivo…»)",
                fg="#a00"
            )
            self._set_estado("Ruta guardada no encontrada.")
            return

        # Caso 3: primera vez -> pedir archivo y guardar
        ruta_sel = filedialog.askopenfilename(
            title="Selecciona el archivo de Códigos Postales",
            filetypes=[
                ("Hojas de calculo", "*.xlsx *.xls *.ods"),
                ("Excel", "*.xlsx *.xls"),
                ("OpenDocument", "*.ods"),
            ]
        )
        if not ruta_sel:
            self._error("No se seleccionó archivo de Códigos Postales.")
            return

        guardar_ultimo_path(ruta_sel, clave=self.CONFIG_KEY_FILE)
        capturar_log_bod1(f"[CP] Ruta de códigos postales guardada: {ruta_sel}", "info")
        self._usar_ruta_y_cargar(ruta_sel)

    def _usar_ruta_y_cargar(self, ruta: str) -> None:
        """Actualiza la UI de inmediato y lanza la carga en segundo plano."""
        self._ruta_excel = ruta
        self.lbl_archivo.config(text=f"Archivo: {Path(ruta).name}", fg="#555")
        self._set_estado("Cargando datos…")
        threading.Thread(target=self._cargar_en_background, args=(ruta,), daemon=True).start()

    def _cargar_en_background(self, ruta: str) -> None:
        try:
            df = self._leer_y_normalizar_excel(Path(ruta))
            df = df.dropna(how="all")
            for c in ("REGIÓN", "COMUNA", "CÓDIGO POSTAL"):
                df[c] = df[c].astype(str).str.strip()
                df[c] = df[c].replace({"nan": "", "None": "", "<NA>": ""})

            # Forzar código postal numérico y limpiar filas incompletas.
            df["CÓDIGO POSTAL"] = (
                df["CÓDIGO POSTAL"]
                .astype(str)
                .str.replace(r"[^0-9]", "", regex=True)
                .str.strip()
            )
            df = df[
                (df["REGIÓN"] != "")
                & (df["COMUNA"] != "")
                & (df["CÓDIGO POSTAL"] != "")
            ]
            df = df.drop_duplicates(subset=["REGIÓN", "COMUNA", "CÓDIGO POSTAL"])

            self.df = df.reset_index(drop=True)
            # Reafirma la ruta usada (por si vino de Cambiar archivo…)
            guardar_ultimo_path(ruta, clave=self.CONFIG_KEY_FILE)

            capturar_log_bod1(f"[CP] Archivo de códigos postales cargado: {ruta}", "info")

            # Actualiza UI en el hilo principal
            self.after(0, lambda: (self._poblar_tree(self.df), self._set_estado("Listo")))
        except Exception as e:
            capturar_log_bod1(f"Error al cargar archivo de códigos postales: {e}", "error")
            self.after(0, partial(self._error, f"No se pudo cargar el archivo:\n{e}"))

    # ----------------------- Lectura y normalización Excel -------------------

    def _leer_y_normalizar_excel(self, path: Path) -> pd.DataFrame:
        """
        Preferente: header=1 (fila 2 visible) + usecols A:D con renombrado seguro.
        Respaldos: header en [2,0,3,4,5], sin encabezado + heurística, inferencia.
        """
        engine = self._excel_engine_for_path(path)

        if path.suffix.lower() == ".ods":
            try:
                df_ods = self._leer_ods_via_content_xml(path)
                df_ods = self._rename_soft(df_ods)
                if self._tiene_columnas_target(df_ods):
                    return df_ods.loc[:, list(self.COLS_TARGET)]
            except Exception as e:
                capturar_log_bod1(f"[CP] Fallback ODS XML falló: {e}", "warning")

        # Prepara lista de hojas por defecto
        sheet_names = [0]

        # 0) INTENTO PREFERENTE: header=1, A:D
        try:
            try:
                xls = pd.ExcelFile(path, engine=engine)
                sheet_names = xls.sheet_names or [0]
            except Exception:
                sheet_names = [0]

            for sheet in sheet_names:
                try:
                    df = pd.read_excel(
                        path,
                        sheet_name=sheet,
                        header=1,            # fila 2 visible
                        usecols="A:D",       # A..D esperado
                        dtype=str,
                        engine=engine,
                    )
                    capturar_log_bod1(f"[CP] preferente header=1 A:D -> cols={list(df.columns)} shape={df.shape}", "info")

                    df = self._rename_soft(df)
                    if self._tiene_columnas_target(df):
                        return df.loc[:, list(self.COLS_TARGET)]
                    else:
                        faltan = set(self.COLS_TARGET) - set(df.columns)
                        capturar_log_bod1(f"[CP] preferente faltan: {faltan}", "warning")
                except Exception as e:
                    capturar_log_bod1(f"[CP] preferente fallo hoja '{sheet}': {e}", "warning")
        except Exception as e:
            capturar_log_bod1(f"[CP] preferente error general: {e}", "error")

        # 1) RESPALDO: headers en orden preferido
        try:
            try:
                xls = pd.ExcelFile(path, engine=engine)
                sheet_names = xls.sheet_names or [0]
            except Exception:
                sheet_names = [0]

            for sheet in sheet_names:
                for header_row in self.PREFERRED_HEADER_ROWS:
                    try:
                        df_try = pd.read_excel(path, sheet_name=sheet, header=header_row, dtype=str, engine=engine)
                        capturar_log_bod1(f"[CP] respaldo header={header_row} -> cols={list(df_try.columns)} shape={df_try.shape}", "info")
                        df_norm = self._rename_soft(df_try)
                        if self._tiene_columnas_target(df_norm):
                            return df_norm.loc[:, list(self.COLS_TARGET)]
                        # Caso frecuente: la primera fila trae los encabezados reales
                        df_promoted = self._promover_fila_a_encabezado(df_try)
                        if df_promoted is not None:
                            df_promoted = self._rename_soft(df_promoted)
                            if self._tiene_columnas_target(df_promoted):
                                return df_promoted.loc[:, list(self.COLS_TARGET)]
                    except Exception as e:
                        capturar_log_bod1(f"[CP] respaldo header={header_row} fallo: {e}", "warning")
        except Exception as e:
            capturar_log_bod1(f"[CP] respaldo error general: {e}", "error")

        # 2) RESPALDO: sin encabezado + heurística
        for sheet in sheet_names:
            try:
                df_no_header = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str, engine=engine)
                capturar_log_bod1(f"[CP] sin header -> shape={df_no_header.shape}", "info")

                if not df_no_header.empty and self._fila_parece_encabezado(df_no_header.iloc[0]):
                    df_try = pd.read_excel(path, sheet_name=sheet, header=0, dtype=str, engine=engine)
                    df_norm = self._rename_soft(df_try)
                    if self._tiene_columnas_target(df_norm):
                        return df_norm.loc[:, list(self.COLS_TARGET)]

                if df_no_header.shape[1] >= 4:
                    df_pos = df_no_header.rename(columns={0: "COMUNA", 1: "PROVINCIA", 2: "REGIÓN", 3: "CÓDIGO POSTAL"})
                    df_norm = self._normalizar_columnas(df_pos)
                    if self._tiene_columnas_target(df_norm):
                        return df_norm.loc[:, list(self.COLS_TARGET)]
            except Exception as e:
                capturar_log_bod1(f"[CP] sin header fallo: {e}", "warning")

        # 3) RESPALDO: inferencia por contenido
        for sheet in sheet_names:
            try:
                df_any = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str, engine=engine)
                df_infer = self._inferir_por_contenido(df_any)
                if self._tiene_columnas_target(df_infer):
                    return df_infer.loc[:, list(self.COLS_TARGET)]
            except Exception as e:
                capturar_log_bod1(f"[CP] inferencia fallo: {e}", "warning")

        if path.suffix.lower() == ".ods":
            raise ValueError("No se pudo leer el archivo .ods. Instala odfpy: pip install odfpy")

        raise ValueError(
            "No se pudieron detectar las columnas. Asegúrate de que el archivo contenga "
            "las columnas Región, Comuna (o Localidad) y Código Postal."
        )

    def _rename_soft(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renombrado fuerte + suave a REGIÓN/COMUNA/CÓDIGO POSTAL."""
        df = df.copy()
        df.rename(columns={
            "Comuna/Localidad": "COMUNA",
            "Comuna": "COMUNA",
            "Localidad": "COMUNA",
            "Provincia": "PROVINCIA",
            "Region": "REGIÓN",
            "Región": "REGIÓN",
            "Codigo Postal": "CÓDIGO POSTAL",
            "Código Postal": "CÓDIGO POSTAL",
        }, inplace=True)

        def _norm(s: str) -> str:
            s = str(s).strip().lower()
            return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

        for col in list(df.columns):
            k = _norm(col)
            if k in self.COL_SYNONYMS:
                df.rename(columns={col: self.COL_SYNONYMS[k]}, inplace=True)
            else:
                if "comuna" in k or "localidad" in k:
                    df.rename(columns={col: "COMUNA"}, inplace=True)
                elif "region" in k:
                    df.rename(columns={col: "REGIÓN"}, inplace=True)
                elif ("codigo" in k and "postal" in k) or ("ubigeo" in k) or k == "cp":
                    df.rename(columns={col: "CÓDIGO POSTAL"}, inplace=True)

        for c in ("REGIÓN", "COMUNA", "CÓDIGO POSTAL"):
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()

        return df

    def _promover_fila_a_encabezado(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Promueve la primera fila como encabezado si el DataFrame no trae nombres útiles."""
        if df is None or df.empty:
            return None
        try:
            first_row = df.iloc[0].fillna("").astype(str).str.strip()
            if first_row.eq("").all():
                return None
            promoted = df.iloc[1:].copy().reset_index(drop=True)
            promoted.columns = first_row.tolist()
            return promoted
        except Exception:
            return None

    def _normalizar_columnas(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._rename_soft(df)

    def _tiene_columnas_target(self, df: pd.DataFrame) -> bool:
        return all(c in df.columns for c in self.COLS_TARGET)

    def _fila_parece_encabezado(self, fila0: pd.Series) -> bool:
        keys = {"region", "región", "comuna", "comuna/localidad", "codigo postal", "código postal", "codigo ubigeo", "ubigeo", "cp"}
        vals = set(self._norm_text(v) for v in fila0.values)
        return any(k in vals for k in keys)

    def _inferir_por_contenido(self, df_any: pd.DataFrame) -> pd.DataFrame:
        sample = df_any.head(100).copy()
        ncols = sample.shape[1]
        if ncols == 0:
            raise ValueError("Archivo vacío o sin columnas.")

        def is_cp_like(s: str) -> bool:
            s = (s or "").strip()
            return s.isdigit() and 4 <= len(s) <= 8

        def clean_digits(s: str) -> str:
            return "".join(ch for ch in str(s) if ch.isdigit())

        cp_scores = {c: sum(1 for v in sample.iloc[:, c].astype(str) if is_cp_like(v)) / len(sample)
                     for c in range(ncols)}
        cp_col = max(cp_scores, key=cp_scores.get)
        if cp_scores[cp_col] < 0.3:
            sdigits = sample.applymap(clean_digits)
            cp_scores2 = {c: sum(1 for v in sdigits.iloc[:, c] if is_cp_like(v)) / len(sdigits)
                          for c in range(ncols)}
            cp_col = max(cp_scores2, key=cp_scores2.get)

        text_candidates = [c for c in range(ncols) if c != cp_col]

        KEY_REG = {"region", "región", "rm", "metropolitana", "valparaiso", "biobio", "araucania", "ohiggins"}
        KEY_COM = {"comuna", "localidad", "ciudad", "poblacion", "barrio"}

        def norm(s: str) -> str:
            s = str(s).strip().lower()
            s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
            return s

        def score_keys(col, keys):
            vals = [norm(v) for v in sample.iloc[:, col].astype(str).tolist()]
            return sum(any(k in v for v in vals) for k in keys)

        reg_scores = {c: score_keys(c, KEY_REG) for c in text_candidates} or {text_candidates[0]: 0}
        com_scores = {c: score_keys(c, KEY_COM) for c in text_candidates} or {text_candidates[-1]: 0}

        region_col = max(reg_scores, key=reg_scores.get)
        restante = [c for c in text_candidates if c != region_col] or [region_col]
        comuna_col = max({c: com_scores.get(c, 0) for c in restante}, key=lambda k: com_scores.get(k, 0))

        out = pd.DataFrame({
            "REGIÓN": df_any.iloc[:, region_col].astype(str).str.strip(),
            "COMUNA": df_any.iloc[:, comuna_col].astype(str).str.strip(),
            "CÓDIGO POSTAL": df_any.iloc[:, cp_col].astype(str).str.strip(),
        })
        return self._rename_soft(out)

    def _leer_ods_via_content_xml(self, path: Path) -> pd.DataFrame:
        ns = {
            "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
            "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        }

        def cell_text(cell) -> str:
            vals = []
            for p in cell.findall(".//text:p", ns):
                t = "".join(p.itertext()).strip()
                if t:
                    vals.append(t)
            return " ".join(vals)

        with zipfile.ZipFile(path, "r") as zf:
            root = ET.fromstring(zf.read("content.xml"))

        rows = None
        for t in root.findall(".//table:table", ns):
            tmp_rows = []
            for tr in t.findall("table:table-row", ns):
                rep_rows = int(
                    tr.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-rows-repeated", "1")
                )
                row = []
                for tc in tr.findall("table:table-cell", ns):
                    rep_cols = int(
                        tc.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated", "1")
                    )
                    txt = cell_text(tc)
                    row.extend([txt] * rep_cols)
                while row and row[-1] == "":
                    row.pop()
                for _ in range(rep_rows):
                    tmp_rows.append(list(row))
            if any(any(str(c).strip() for c in r) for r in tmp_rows):
                rows = tmp_rows
                break

        if not rows:
            raise ValueError("ODS sin filas de datos")

        max_cols = max((len(r) for r in rows), default=0)
        rows = [r + [""] * (max_cols - len(r)) for r in rows]
        headers = [str(v).strip() if str(v).strip() else f"col_{i+1}" for i, v in enumerate(rows[1])]
        return pd.DataFrame(rows[2:], columns=headers)

    # ----------------------------- Búsqueda (UI) -----------------------------

    def _on_search_changed(self, _evt=None) -> None:
        if self._creating:
            return
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(250, self._buscar_now)

    def _buscar_now(self) -> None:
        termino_raw = self.entry_busqueda.get().strip()
        if not termino_raw:
            self._poblar_tree(self.df)
            self._set_estado("Listo")
            return

        termino = self._norm_text(termino_raw)
        df = self.df.copy()
        if df.empty:
            self._set_estado("No hay datos cargados.")
            return

        def norm_series(s: Iterable) -> pd.Series:
            return pd.Series([self._norm_text(str(x)) for x in s])

        mask = (
            norm_series(df["COMUNA"]).str.contains(termino, na=False)
            | norm_series(df["REGIÓN"]).str.contains(termino, na=False)
            | norm_series(df["CÓDIGO POSTAL"]).str.contains(termino, na=False)
        )

        filtrado = df.loc[mask]
        self._poblar_tree(filtrado)
        capturar_log_bod1(f"Búsqueda: '{termino_raw}' → resultados: {len(filtrado)}", "info")
        self._set_estado(f"{len(filtrado)} resultado(s)")

    def _clear_search(self) -> None:
        self.entry_busqueda.delete(0, "end")
        self._poblar_tree(self.df)
        self._set_estado("Búsqueda limpiada")

    # ----------------------------- Poblado Tree ------------------------------

    def _poblar_tree(self, df: pd.DataFrame) -> None:
        self.tree.delete(*self.tree.get_children())

        if df is None or df.empty:
            self.btn_copiar["state"] = "disabled"
            return

        max_rows = 10000
        for _, row in df.head(max_rows).iterrows():
            self.tree.insert("", "end", values=(
                row.get("REGIÓN", ""),
                row.get("COMUNA", ""),
                row.get("CÓDIGO POSTAL", "")
            ))

        self._autoajustar_columnas(sample_df=df.head(120))
        self.btn_copiar["state"] = "disabled"
        self._creating = False

    def _autoajustar_columnas(self, sample_df: pd.DataFrame) -> None:
        def char_to_px(chars: int) -> int:
            return max(90, min(int(chars * 7.5) + 24, 420))

        for col in self.COLS_TARGET:
            max_len = max([len(str(col))] + [len(str(v)) for v in sample_df.get(col, pd.Series()).astype(str).tolist()] + [6])
            self.tree.column(col, width=char_to_px(max_len), stretch=True)

    # ----------------------------- Interacciones -----------------------------

    def _on_tree_select(self, _evt=None) -> None:
        self.btn_copiar["state"] = "normal" if self.tree.selection() else "disabled"

    def _copiar_codigo_postal(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Copia", "Seleccione una fila primero.")
            return
        item = self.tree.item(sel[0])
        try:
            codigo_postal = item["values"][2]
        except Exception:
            messagebox.showwarning("Copia", "No se pudo obtener el Código Postal de la fila seleccionada.")
            return

        self.clipboard_clear()
        self.clipboard_append(str(codigo_postal))
        self.update_idletasks()
        self._set_estado(f"Código Postal copiado: {codigo_postal}")
        messagebox.showinfo("Copiado", f"Código Postal copiado: {codigo_postal}")

    def _cambiar_archivo(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Selecciona el archivo de Códigos Postales",
            filetypes=[
                ("Hojas de calculo", "*.xlsx *.xls *.ods"),
                ("Excel", "*.xlsx *.xls"),
                ("OpenDocument", "*.ods"),
            ]
        )
        if not ruta:
            return
        guardar_ultimo_path(ruta, clave=self.CONFIG_KEY_FILE)
        capturar_log_bod1(f"[CP] Ruta cambiada por el usuario: {ruta}", "info")
        self._usar_ruta_y_cargar(ruta)

    # -------------------------------- Utils ----------------------------------

    def _norm_text(self, s: str) -> str:
        s = str(s).strip()
        s = " ".join(s.split())
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return s.lower()

    def _set_estado(self, msg: str) -> None:
        self.lbl_estado.config(text=msg)

    def _error(self, mensaje: str) -> None:
        messagebox.showerror("Error", mensaje)
        self.destroy()
