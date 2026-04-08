import json
import platform
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import unicodedata

import pandas as pd
from app.gui.inventario_view import _clean_for_view, _normalize_headers
from app.utils.app_dirs import CONFIG_DIR, ensure_file
from app.utils.utils import guardar_ultimo_path, load_config as load_app_config
from app.printer.printer_etiquetas import generar_etiqueta_excel, imprimir_excel

CONFIG_PATH = ensure_file(
    CONFIG_DIR / "excel_printer_config.json",
    legacy_candidates=(
        Path("app/config/excel_printer_config.json"),
        Path("config/excel_printer_config.json"),
    ),
)
CLIENTES_PATH_KEY = "clientes_proveedores_path"
INVENTORY_PATH_KEY = "archivo_inventario"


def cargar_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def cargar_clientes(path_excel):
    try:
        return pd.read_excel(path_excel, sheet_name="Clientes")
    except Exception:
        return pd.read_excel(path_excel)


def _normalizar_rut(rut: str) -> str:
    return str(rut).replace(".", "").replace("-", "").strip().upper()


def _normalizar_columna(valor: str) -> str:
    txt = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii")
    return txt.strip().lower().replace("_", " ")


def _normalizar_texto(valor: str) -> str:
    txt = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(txt.strip().lower().split())


def _buscar_columna(columnas_lower, *opciones):
    for opcion in opciones:
        encontrada = columnas_lower.get(_normalizar_columna(opcion))
        if encontrada:
            return encontrada
    return None


def buscar_cliente_por_rut(df_clientes, rut):
    if df_clientes is None or df_clientes.empty:
        return None

    columnas_lower = {_normalizar_columna(col): col for col in df_clientes.columns}
    col_rut = _buscar_columna(columnas_lower, "rut")
    if col_rut is None:
        return None

    rut_norm = _normalizar_rut(rut)
    serie_rut = df_clientes[col_rut].astype(str).map(_normalizar_rut)
    fila = df_clientes[serie_rut == rut_norm]
    if fila.empty:
        return None

    datos = fila.iloc[0]
    col_razsoc = _buscar_columna(columnas_lower, "razsoc", "razon social", "cliente", "nombre cliente")
    col_dir = _buscar_columna(columnas_lower, "dir", "direccion", "domicilio")
    col_comuna = _buscar_columna(columnas_lower, "comuna")
    col_ciudad = _buscar_columna(columnas_lower, "ciudad")

    return {
        "razsoc": datos.get(col_razsoc, "") if col_razsoc else "",
        "dir": datos.get(col_dir, "") if col_dir else "",
        "comuna": datos.get(col_comuna, "") if col_comuna else "",
        "ciudad": datos.get(col_ciudad, "") if col_ciudad else "",
    }


def obtener_impresoras_disponibles():
    system = platform.system()
    impresoras = []
    if system == "Windows":
        try:
            import win32print

            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            raw = win32print.EnumPrinters(flags)
            nombres = []
            for item in raw:
                if isinstance(item, (tuple, list)) and len(item) >= 3:
                    nombres.append(str(item[2]))
                elif isinstance(item, dict) and item.get("pPrinterName"):
                    nombres.append(str(item.get("pPrinterName")))
            impresoras = sorted({n.strip() for n in nombres if n and n.strip()})
        except Exception:
            impresoras = []
    elif system == "Linux":
        try:
            output = subprocess.check_output(["lpstat", "-a"]).decode()
            impresoras = [line.split()[0] for line in output.strip().split("\n") if line]
        except Exception:
            impresoras = []
    return impresoras


def cargar_inventario_productos(path_excel):
    suffix = Path(path_excel).suffix.lower()
    if suffix == ".xlsx":
        df = pd.read_excel(path_excel, engine="openpyxl")
    elif suffix == ".xls":
        df = pd.read_excel(path_excel, engine="xlrd")
    else:
        raise ValueError("Extension de archivo no soportada. Usa .xlsx o .xls")

    df = _normalize_headers(df)
    return _clean_for_view(df)


def _set_windows_default_printer(printer_alias: str) -> None:
    if platform.system() != "Windows" or not (printer_alias or "").strip():
        return
    try:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        raw = win32print.EnumPrinters(flags)
        names = []
        for item in raw:
            if isinstance(item, (tuple, list)) and len(item) >= 3:
                names.append(str(item[2]).strip())
            elif isinstance(item, dict) and item.get("pPrinterName"):
                names.append(str(item.get("pPrinterName")).strip())

        target = printer_alias.strip()
        target_low = target.lower()
        resolved = target
        for n in names:
            if n and n.lower() == target_low:
                resolved = n
                break
        else:
            for n in names:
                if n and (target_low in n.lower() or n.lower() in target_low):
                    resolved = n
                    break

        win32print.SetDefaultPrinter(resolved)
    except Exception:
        # No bloquear impresión de etiquetas por fallo al cambiar default.
        pass


def _cleanup_temp_files_later(paths, delay_seconds=180):
    """
    Limpia archivos temporales en diferido para evitar que Excel/soffice
    intente abrir un archivo que ya fue eliminado.
    """
    def _run():
        time.sleep(delay_seconds)
        for p in paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


def crear_editor_etiqueta(df_clientes=None, parent=None):
    config = cargar_config()
    app_config = load_app_config() or {}
    printer_name_default = config.get("label_printer_name") or config.get("printer_name", "")
    clientes_path_guardado = config.get(CLIENTES_PATH_KEY, "")
    inventario_path_guardado = app_config.get(INVENTORY_PATH_KEY, "")
    estado = {"df_clientes": df_clientes, "df_inventario": pd.DataFrame()}

    ventana = tk.Toplevel(parent)
    ventana.title("Editor de Etiquetas 10x10 cm")
    ventana.geometry("1280x860")
    ventana.minsize(1120, 760)
    ventana.configure(bg="#EEF2F9")

    style = ttk.Style(ventana)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("EditorBg.TFrame", background="#EEF2F9")
    style.configure("Card.TFrame", background="#FFFFFF")
    style.configure("HeaderTitle.TLabel", font=("Segoe UI Semibold", 17), foreground="#10203F", background="#EEF2F9")
    style.configure("HeaderSub.TLabel", font=("Segoe UI", 10), foreground="#4C5D7A", background="#EEF2F9")
    style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 11), foreground="#1A2A4D", background="#FFFFFF")
    style.configure("Body.TLabel", font=("Segoe UI", 10), foreground="#223251", background="#FFFFFF")
    style.configure("Path.TLabel", font=("Consolas", 9), foreground="#2F3C55", background="#FFFFFF")
    style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(12, 7))
    style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(12, 7))

    shell = ttk.Frame(ventana, style="EditorBg.TFrame", padding=16)
    shell.pack(fill="both", expand=True)

    header = ttk.Frame(shell, style="EditorBg.TFrame")
    header.pack(fill="x", pady=(0, 12))
    ttk.Label(header, text="Editor de Etiquetas", style="HeaderTitle.TLabel").pack(anchor="w")
    ttk.Label(
        header,
        text="Trabaja etiquetas de despacho o etiquetas de producto desde una sola pantalla.",
        style="HeaderSub.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    mode_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
    mode_card.pack(fill="x")
    ttk.Label(mode_card, text="Modo de etiqueta", style="CardTitle.TLabel").pack(anchor="w")
    mode_var = tk.StringVar(value="despacho")
    mode_row = ttk.Frame(mode_card, style="Card.TFrame")
    mode_row.pack(fill="x", pady=(8, 0))
    ttk.Radiobutton(mode_row, text="Despacho", variable=mode_var, value="despacho").pack(side="left")
    ttk.Radiobutton(mode_row, text="Etiqueta productos", variable=mode_var, value="producto").pack(side="left", padx=(14, 0))

    source_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
    source_card.pack(fill="x", pady=(12, 0))
    ttk.Label(source_card, text="Origen de clientes", style="CardTitle.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    campos = {
        "rut": "RUT",
        "razsoc": "Cliente",
        "dir": "Direccion",
        "comuna": "Comuna",
        "guia": "Guia",
        "bultos": "Bultos",
        "transporte": "Transporte",
    }

    entradas = {}
    status_var = tk.StringVar(value="Completa el formulario para imprimir.")

    lbl_excel = ttk.Label(source_card, text="Archivo clientes: No cargado", style="Path.TLabel")
    lbl_excel.grid(row=1, column=0, sticky="w", pady=(0, 8))
    source_card.columnconfigure(0, weight=1)
    lbl_inventory = ttk.Label(source_card, text="Archivo inventario: No cargado", style="Path.TLabel")
    lbl_inventory.grid(row=2, column=0, sticky="w", pady=(0, 4))

    def _short_path(p):
        if not p:
            return "No cargado"
        p = str(p)
        return p if len(p) <= 90 else f"...{p[-87:]}"

    def cargar_excel_clientes(path):
        try:
            estado["df_clientes"] = cargar_clientes(path)
            lbl_excel.config(text=f"Archivo clientes: {_short_path(path)}")
            config[CLIENTES_PATH_KEY] = str(path)
            guardar_config(config)
            status_var.set(f"Clientes cargados: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el Excel de clientes:\n{e}")

    def seleccionar_excel_clientes():
        path = filedialog.askopenfilename(
            title="Selecciona Excel de clientes y proveedores",
            filetypes=[("Excel Files", "*.xlsx *.xls")],
        )
        if not path:
            return
        cargar_excel_clientes(path)

    ttk.Button(source_card, text="Cargar Excel Clientes", style="Secondary.TButton", command=seleccionar_excel_clientes).grid(
        row=1, column=1, sticky="e", pady=(0, 8)
    )

    def cargar_excel_inventario(path):
        try:
            estado["df_inventario"] = cargar_inventario_productos(path)
            lbl_inventory.config(text=f"Archivo inventario: {_short_path(path)}")
            guardar_ultimo_path(str(path), clave=INVENTORY_PATH_KEY)
            status_var.set(f"Inventario cargado: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el Excel de inventario:\n{e}")

    def seleccionar_excel_inventario():
        path = filedialog.askopenfilename(
            title="Selecciona archivo de inventario",
            filetypes=[("Excel Files", "*.xlsx *.xls")],
        )
        if not path:
            return
        cargar_excel_inventario(path)

    ttk.Button(source_card, text="Cargar Excel Inventario", style="Secondary.TButton", command=seleccionar_excel_inventario).grid(
        row=2, column=1, sticky="e", pady=(0, 4)
    )

    if df_clientes is not None:
        lbl_excel.config(text="Archivo clientes: Cargado en memoria")
    elif clientes_path_guardado and Path(clientes_path_guardado).exists():
        cargar_excel_clientes(clientes_path_guardado)
    if inventario_path_guardado and Path(inventario_path_guardado).exists():
        cargar_excel_inventario(inventario_path_guardado)

    forms_host = ttk.Frame(shell, style="EditorBg.TFrame")
    forms_host.pack(fill="x", expand=False, pady=(12, 0))

    form_card = ttk.Frame(forms_host, style="Card.TFrame", padding=14)
    ttk.Label(form_card, text="Datos de etiqueta de despacho", style="CardTitle.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    form_card.columnconfigure(1, weight=1)

    for idx, (key, label) in enumerate(campos.items(), start=1):
        ttk.Label(form_card, text=label + ":", style="Body.TLabel").grid(row=idx, column=0, sticky="e", pady=5, padx=(0, 10))
        entry = ttk.Entry(form_card, width=48)
        entry.grid(row=idx, column=1, pady=5, sticky="ew")
        entradas[key] = entry

    producto_card = ttk.Frame(forms_host, style="Card.TFrame", padding=14)
    ttk.Label(producto_card, text="Etiquetas de producto", style="CardTitle.TLabel").grid(
        row=0, column=0, columnspan=4, sticky="w", pady=(0, 8)
    )
    ttk.Label(
        producto_card,
        text="Busca por código o nombre del producto, selecciónalo y genera su etiqueta con datos de inventario.",
        style="Body.TLabel",
    ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))
    producto_card.columnconfigure(1, weight=1)
    producto_card.columnconfigure(2, weight=1)
    producto_card.columnconfigure(3, weight=1)
    producto_card.columnconfigure(4, weight=1)

    producto_entries = {}
    producto_labels = {}
    product_search_var = tk.StringVar(value="")

    ttk.Label(producto_card, text="Buscar producto:", style="Body.TLabel").grid(row=2, column=0, sticky="e", padx=(0, 10), pady=5)
    product_search_entry = ttk.Entry(producto_card, textvariable=product_search_var, width=50)
    product_search_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)

    product_results = ttk.Treeview(
        producto_card,
        columns=("Código", "Producto", "Ubicación", "Lote", "N° Serie", "Fecha Vencimiento", "Saldo Stock"),
        show="headings",
        height=8,
    )
    result_widths = {
        "Código": 100,
        "Producto": 240,
        "Ubicación": 120,
        "Lote": 110,
        "N° Serie": 120,
        "Fecha Vencimiento": 120,
        "Saldo Stock": 100,
    }
    for col in product_results["columns"]:
        product_results.heading(col, text=col, anchor="center")
        product_results.column(col, width=result_widths.get(col, 120), minwidth=90, anchor="center", stretch=True)

    result_scroll = ttk.Scrollbar(producto_card, orient="vertical", command=product_results.yview)
    product_results.configure(yscrollcommand=result_scroll.set)
    product_results.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(6, 10))
    result_scroll.grid(row=3, column=4, sticky="ns", pady=(6, 10))
    producto_card.rowconfigure(3, weight=1)

    producto_campos = {
        "codigo": "Código",
        "producto": "Producto",
        "bodega": "Bodega",
        "ubicacion": "Ubicación",
        "lote_serie": "Lote / Serie",
        "fecha_vencimiento": "Fecha vencimiento",
        "cantidad": "Cantidad",
        "copias": "Etiquetas",
    }
    for idx, (key, label) in enumerate(producto_campos.items(), start=4):
        label_widget = ttk.Label(producto_card, text=label + ":", style="Body.TLabel")
        label_widget.grid(
            row=idx, column=0, sticky="e", padx=(0, 10), pady=5
        )
        entry = ttk.Entry(producto_card, width=48)
        entry.grid(row=idx, column=1, columnspan=3, sticky="ew", pady=5)
        producto_labels[key] = label_widget
        producto_entries[key] = entry

    producto_layout = {
        "codigo": (4, 0),
        "producto": (5, 0),
        "bodega": (6, 0),
        "ubicacion": (7, 0),
        "lote_serie": (4, 2),
        "fecha_vencimiento": (5, 2),
        "cantidad": (6, 2),
        "copias": (7, 2),
    }
    for key, (row, col) in producto_layout.items():
        producto_labels[key].grid_configure(row=row, column=col, padx=(0, 10), pady=4, sticky="e")
        producto_entries[key].configure(width=30)
        producto_entries[key].grid_configure(row=row, column=col + 1, columnspan=1, padx=(0, 12), pady=4, sticky="ew")

    producto_entries["copias"].insert(0, "1")

    fila_impresora = len(campos) + 1
    impresoras = obtener_impresoras_disponibles()
    printer_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
    printer_card.pack(fill="x", pady=(12, 0))
    ttk.Label(printer_card, text="Impresora y acciones", style="CardTitle.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    printer_card.columnconfigure(1, weight=1)
    ttk.Label(printer_card, text="Impresora:", style="Body.TLabel").grid(row=1, column=0, sticky="e", pady=5, padx=(0, 10))
    combo_impresoras = ttk.Combobox(printer_card, values=impresoras, width=60, state="readonly")
    if printer_name_default:
        combo_impresoras.set(printer_name_default)
    elif impresoras:
        combo_impresoras.set(impresoras[0])
    combo_impresoras.grid(row=1, column=1, pady=5, sticky="ew")

    actions = ttk.Frame(printer_card, style="Card.TFrame")
    actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Label(actions, textvariable=status_var, style="HeaderSub.TLabel").pack(anchor="w", pady=(0, 10))

    def cargar_datos_cliente(event=None):
        rut = entradas["rut"].get()
        cliente = buscar_cliente_por_rut(estado["df_clientes"], rut)
        if cliente:
            for campo in ["razsoc", "dir", "comuna"]:
                entradas[campo].delete(0, tk.END)
                entradas[campo].insert(0, cliente[campo])
            status_var.set("Cliente encontrado y cargado en formulario.")
        else:
            status_var.set("No se encontro cliente para ese RUT.")
            messagebox.showerror("RUT no encontrado", "No se encontro cliente para el RUT ingresado o no has cargado el Excel.")

    entradas["rut"].bind("<Return>", cargar_datos_cliente)

    def validar_campos(data):
        obligatorios = ["rut", "razsoc", "dir", "guia", "bultos"]
        faltantes = [campo for campo in obligatorios if not data.get(campo)]
        if faltantes:
            messagebox.showerror(
                "Campos faltantes",
                "Completa los siguientes campos:\n- " + "\n- ".join(faltantes),
            )
            return False
        try:
            total_bultos = int(str(data.get("bultos", "0")).strip())
            if total_bultos <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Bultos invalido", "El campo Bultos debe ser entero mayor a 0.")
            return False
        return True

    def validar_campos_producto(data):
        obligatorios = ["codigo", "producto", "ubicacion"]
        faltantes = [campo for campo in obligatorios if not str(data.get(campo, "")).strip()]
        if faltantes:
            messagebox.showerror(
                "Campos faltantes",
                "Selecciona un producto valido antes de imprimir.",
            )
            return False
        try:
            total_copias = int(str(data.get("copias", "0")).strip())
            if total_copias <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Etiquetas invalido", "El campo Etiquetas debe ser entero mayor a 0.")
            return False
        return True

    def limpiar_formulario():
        for entry in entradas.values():
            entry.delete(0, tk.END)
        for entry in producto_entries.values():
            entry.delete(0, tk.END)
        producto_entries["copias"].insert(0, "1")
        product_search_var.set("")
        product_results.delete(*product_results.get_children())
        status_var.set("Formulario limpio.")

    def buscar_productos(event=None):
        product_results.delete(*product_results.get_children())
        df_inventario = estado.get("df_inventario")
        term = _normalizar_texto(product_search_var.get())
        if df_inventario is None or df_inventario.empty:
            status_var.set("Carga un archivo de inventario para usar etiquetas de producto.")
            return
        if not term:
            status_var.set("Escribe un código o nombre para buscar productos.")
            return

        code_series = df_inventario["Código"].astype(str).map(_normalizar_texto)
        prod_series = df_inventario["Producto"].astype(str).map(_normalizar_texto)
        terms = [t for t in term.split() if t]
        mask = code_series.apply(lambda value: all(t in value for t in terms)) | prod_series.apply(lambda value: all(t in value for t in terms))
        results = df_inventario.loc[mask, ["Código", "Producto", "Ubicación", "Lote", "N° Serie", "Fecha Vencimiento", "Saldo Stock", "Bodega"]].head(200).reset_index(drop=True)
        for idx, row in results.iterrows():
            product_results.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    row["Código"],
                    row["Producto"],
                    row["Ubicación"],
                    row["Lote"],
                    row["N° Serie"],
                    row["Fecha Vencimiento"],
                    row["Saldo Stock"],
                ),
            )
        estado["producto_resultados"] = results
        status_var.set(f"Productos encontrados: {len(results)}")

    def seleccionar_producto(event=None):
        selection = product_results.selection()
        if not selection:
            return
        results = estado.get("producto_resultados")
        if results is None or results.empty:
            return
        row = results.iloc[int(selection[0])]
        lote = str(row.get("Lote", "") or "").strip()
        serie = str(row.get("N° Serie", "") or "").strip()
        if lote and serie:
            lote_serie = f"Lote: {lote} | Serie: {serie}"
        elif lote:
            lote_serie = f"Lote: {lote}"
        elif serie:
            lote_serie = f"Serie: {serie}"
        else:
            lote_serie = ""

        values_map = {
            "codigo": row.get("Código", ""),
            "producto": row.get("Producto", ""),
            "bodega": row.get("Bodega", ""),
            "ubicacion": row.get("Ubicación", ""),
            "lote_serie": lote_serie,
            "fecha_vencimiento": row.get("Fecha Vencimiento", ""),
            "cantidad": row.get("Saldo Stock", ""),
        }
        for key, value in values_map.items():
            producto_entries[key].delete(0, tk.END)
            producto_entries[key].insert(0, str(value))
        status_var.set(f"Producto seleccionado: {row.get('Producto', '')}")

    product_search_entry.bind("<Return>", buscar_productos)
    product_results.bind("<<TreeviewSelect>>", seleccionar_producto)
    product_results.bind("<Double-1>", seleccionar_producto)

    def generar_y_imprimir():
        try:
            printer_name = combo_impresoras.get().strip()
            if not printer_name:
                messagebox.showerror("Impresora requerida", "Selecciona una etiquetadora antes de imprimir.")
                return
            if impresoras and printer_name not in impresoras:
                messagebox.showerror(
                    "Impresora invalida",
                    "La impresora seleccionada no esta disponible. Vuelve a seleccionarla en la lista.",
                )
                return

            config["printer_name"] = printer_name
            config["label_printer_name"] = printer_name
            guardar_config(config)
            _set_windows_default_printer(printer_name)

            archivos_temporales = []

            if mode_var.get() == "producto":
                data = {k: v.get() for k, v in producto_entries.items()}
                if not validar_campos_producto(data):
                    return
                total_bultos = int(data["copias"])
                if total_bultos > 10:
                    continuar = messagebox.askyesno(
                        "Confirmar impresion",
                        f"Vas a imprimir {total_bultos} etiquetas. Deseas continuar?",
                    )
                    if not continuar:
                        status_var.set("Impresion cancelada por el usuario.")
                        return

                for _ in range(total_bultos):
                    etiqueta_data = {
                        "label_mode": "producto",
                        "codigo": data["codigo"],
                        "producto": data["producto"],
                        "bodega": data["bodega"],
                        "ubicacion": data["ubicacion"],
                        "lote_serie": data["lote_serie"],
                        "fecha_vencimiento": data["fecha_vencimiento"],
                        "cantidad": data["cantidad"],
                    }
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_xlsx:
                        output_path = Path(temp_xlsx.name)
                    archivos_temporales.append(str(output_path))
                    generar_etiqueta_excel(etiqueta_data, output_path)
                    imprimir_excel(output_path, printer_name or None)
                _cleanup_temp_files_later(archivos_temporales, delay_seconds=180)
                status_var.set(f"Se enviaron {total_bultos} etiquetas de producto a impresion.")
                messagebox.showinfo("Listo", f"Se enviaron {total_bultos} etiquetas de producto a impresion.")
                return

            data = {k: v.get() for k, v in entradas.items()}
            if not validar_campos(data):
                return

            total_bultos = int(data["bultos"])
            if total_bultos > 10:
                continuar = messagebox.askyesno(
                    "Confirmar impresion",
                    f"Vas a imprimir {total_bultos} etiquetas. Deseas continuar?",
                )
                if not continuar:
                    status_var.set("Impresion cancelada por el usuario.")
                    return

            for indice in range(1, total_bultos + 1):
                etiqueta_data = dict(data)
                etiqueta_data["bultos"] = f"{indice}/{total_bultos}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_xlsx:
                    output_path = Path(temp_xlsx.name)
                archivos_temporales.append(str(output_path))
                generar_etiqueta_excel(etiqueta_data, output_path)
                imprimir_excel(output_path, printer_name or None)

            _cleanup_temp_files_later(archivos_temporales, delay_seconds=180)
            status_var.set(f"Se enviaron {total_bultos} etiquetas a impresion.")
            messagebox.showinfo("Listo", f"Se enviaron {total_bultos} etiquetas a impresion.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar o imprimir la etiqueta:\n{e}")

    btn_row = ttk.Frame(actions, style="EditorBg.TFrame")
    btn_row.pack(fill="x")
    ttk.Button(btn_row, text="Imprimir Etiqueta", style="Primary.TButton", command=generar_y_imprimir).pack(
        side="left"
    )
    ttk.Button(btn_row, text="Limpiar Formulario", style="Secondary.TButton", command=limpiar_formulario).pack(
        side="left", padx=(10, 0)
    )

    def actualizar_modo(*_args):
        if mode_var.get() == "producto":
            form_card.pack_forget()
            producto_card.pack(fill="both", expand=True)
            product_search_entry.focus_set()
            status_var.set("Modo etiqueta productos activo. Busca por código o nombre del producto.")
        else:
            producto_card.pack_forget()
            form_card.pack(fill="x", pady=(0, 0))
            entradas["rut"].focus_set()
            status_var.set("Modo despacho activo. Completa el formulario para imprimir.")

    mode_var.trace_add("write", actualizar_modo)
    actualizar_modo()

    return ventana
