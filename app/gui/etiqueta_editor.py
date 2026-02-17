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
from app.printer.printer_etiquetas import generar_etiqueta_excel, imprimir_excel

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "excel_printer_config.json"
CLIENTES_PATH_KEY = "clientes_proveedores_path"


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
    printer_name_default = config.get("printer_name", "")
    clientes_path_guardado = config.get(CLIENTES_PATH_KEY, "")
    estado = {"df_clientes": df_clientes}

    ventana = tk.Toplevel(parent)
    ventana.title("Editor de Etiquetas 10x10 cm")
    ventana.geometry("700x620")
    ventana.resizable(False, False)
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
        text="Completa datos del cliente y envia etiquetas 10x10 a la impresora seleccionada.",
        style="HeaderSub.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    source_card = ttk.Frame(shell, style="Card.TFrame", padding=12)
    source_card.pack(fill="x")
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

    if df_clientes is not None:
        lbl_excel.config(text="Archivo clientes: Cargado en memoria")
    elif clientes_path_guardado and Path(clientes_path_guardado).exists():
        cargar_excel_clientes(clientes_path_guardado)

    form_card = ttk.Frame(shell, style="Card.TFrame", padding=14)
    form_card.pack(fill="x", pady=(12, 0))
    ttk.Label(form_card, text="Datos de etiqueta", style="CardTitle.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    form_card.columnconfigure(1, weight=1)

    for idx, (key, label) in enumerate(campos.items(), start=1):
        ttk.Label(form_card, text=label + ":", style="Body.TLabel").grid(row=idx, column=0, sticky="e", pady=5, padx=(0, 10))
        entry = ttk.Entry(form_card, width=48)
        entry.grid(row=idx, column=1, pady=5, sticky="ew")
        entradas[key] = entry

    fila_impresora = len(campos) + 1
    ttk.Label(form_card, text="Impresora:", style="Body.TLabel").grid(row=fila_impresora, column=0, sticky="e", pady=5, padx=(0, 10))
    impresoras = obtener_impresoras_disponibles()
    combo_impresoras = ttk.Combobox(form_card, values=impresoras, width=46, state="readonly")
    if printer_name_default:
        combo_impresoras.set(printer_name_default)
    elif impresoras:
        combo_impresoras.set(impresoras[0])
    combo_impresoras.grid(row=fila_impresora, column=1, pady=5, sticky="ew")

    actions = ttk.Frame(shell, style="EditorBg.TFrame")
    actions.pack(fill="x", pady=(14, 0))
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

    def limpiar_formulario():
        for entry in entradas.values():
            entry.delete(0, tk.END)
        status_var.set("Formulario limpio.")

    def generar_y_imprimir():
        try:
            data = {k: v.get() for k, v in entradas.items()}
            printer_name = combo_impresoras.get().strip()

            if not validar_campos(data):
                return
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
            guardar_config(config)

            total_bultos = int(data["bultos"])
            if total_bultos > 10:
                continuar = messagebox.askyesno(
                    "Confirmar impresion",
                    f"Vas a imprimir {total_bultos} etiquetas. Deseas continuar?",
                )
                if not continuar:
                    status_var.set("Impresion cancelada por el usuario.")
                    return

            archivos_temporales = []
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

    entradas["rut"].focus_set()

    return ventana
