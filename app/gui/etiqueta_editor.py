"""
✅ Código completo unificado para impresión de etiquetas Zebra en versión Desktop
✔️ Con verificación de conexión y almacenamiento correcto de ruta de Excel
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import socket
import json
from pathlib import Path
from datetime import datetime
import threading
import logging

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "user_config.json"
LOG_PATH = Path("logs")
LOG_PATH.mkdir(exist_ok=True)
LOG_FILE = LOG_PATH / f"etiquetas_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def cargar_configuracion():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_configuracion(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def verificar_conexion_zebra(ip: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def obtener_ruta_excel():
    config = cargar_configuracion()
    ruta = config.get("ruta_excel")
    if ruta and Path(ruta).exists():
        return ruta
    nueva_ruta = filedialog.askopenfilename(
        title="Selecciona el archivo 'etiqueta pedido.xlsx'",
        filetypes=[("Archivos Excel", "*.xlsx")]
    )
    if nueva_ruta:
        config["ruta_excel"] = nueva_ruta
        guardar_configuracion(config)
        return nueva_ruta
    else:
        messagebox.showerror("Archivo no seleccionado", "No se seleccionó ningún archivo de etiquetas.")
        exit()

def imprimir_zebra_zpl(zpl: str, ip: str, port: int, cantidad: int = 1):
    if not verificar_conexion_zebra(ip, port):
        if messagebox.askretrycancel("Conexión fallida", f"No se pudo conectar con Zebra en {ip}:{port}.¿Quieres escanear y actualizar la IP automáticamente?"):
            encontrados = escanear_dispositivos_zebra()
            if encontrados:
                ip_nuevo = encontrados[0]
                config = cargar_configuracion()
                config["zebra_ip"] = ip_nuevo
                guardar_configuracion(config)
                messagebox.showinfo("Zebra encontrada", f"Nueva IP detectada: {ip_nuevo}Configuración actualizada.")
            else:
                messagebox.showwarning("Escaneo fallido", "No se detectó ninguna impresora Zebra en la red.")
        return
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            for _ in range(cantidad):
                s.sendall(zpl.encode("utf-8"))
        logging.info(f"{cantidad} etiquetas enviadas a Zebra {ip}:{port}")
        messagebox.showinfo("Impresión enviada", f"{cantidad} etiqueta(s) enviada(s) a Zebra ({ip}:{port})")
    except Exception as e:
        logging.error(f"Error al imprimir en Zebra: {str(e)}")
        messagebox.showerror("Error en impresión", str(e))

# (El resto del código permanece igual...)
def generar_zpl_10x10(data: dict) -> str:
    return f"""^XA
^PW800
^LL800
^CF0,40
^FO50,30^FD{data['razsoc']}^FS
^FO50,100^A0N,30,30^FDDirección:^FS
^FO300,100^A0N,30,30^FD{data['dir']}^FS
^FO50,150^A0N,30,30^FDCiudad:^FS
^FO300,150^A0N,30,30^FD{data['ciudad']}^FS
^FO50,200^A0N,30,30^FDComuna:^FS
^FO300,200^A0N,30,30^FD{data['comuna']}^FS
^FO50,250^A0N,30,30^FDGuía:^FS
^FO300,250^A0N,30,30^FD{data['guia']}^FS
^FO50,300^A0N,30,30^FDDespacho:^FS
^FO300,300^A0N,30,30^FD{data['transporte']}^FS
^FO50,350^A0N,30,30^FDBULTO:^FS
^FO300,350^A0N,30,30^FD{data['bultos']}^FS
^FO50,420^BCN,100,Y,N,N
^FD{data['guia']}^FS
^XZ"""

def cargar_clientes(path_excel):
    xls = pd.ExcelFile(path_excel)
    return xls.parse("Clientes")

def buscar_cliente_por_rut(df_clientes, rut):
    fila = df_clientes[df_clientes['rut'] == rut.strip()]
    if not fila.empty:
        datos = fila.iloc[0]
        return {
            "razsoc": datos.get("razsoc", ""),
            "dir": datos.get("dir", ""),
            "comuna": datos.get("comuna", ""),
            "ciudad": datos.get("ciudad", "")
        }
    return None

def escanear_dispositivos_zebra(puerto=9100):
    dispositivos = []
    base_ip = "192.168.0."
    for i in range(1, 255):
        ip = f"{base_ip}{i}"
        try:
            with socket.create_connection((ip, puerto), timeout=0.3):
                dispositivos.append(ip)
        except:
            continue
    return dispositivos

def crear_editor_etiqueta(df_clientes: pd.DataFrame):
    root = tk.Tk()
    root.title("Etiquetas Zebra 10x10")

    config = cargar_configuracion()
    status_var = tk.StringVar(value="🟡 Estado: Desconocido")

    menu_bar = tk.Menu(root)
    config_menu = tk.Menu(menu_bar, tearoff=0)

    ip_var = tk.StringVar(value=config.get("zebra_ip", "192.168.0.100"))
    port_var = tk.StringVar(value=str(config.get("zebra_port", 9100)))

    def actualizar_config():
        config["zebra_ip"] = ip_var.get()
        config["zebra_port"] = int(port_var.get())
        guardar_configuracion(config)
        messagebox.showinfo("Configuración guardada", f"IP: {ip_var.get()} | Puerto: {port_var.get()}")

    def actualizar_status(ip, port):
        try:
            with socket.create_connection((ip, int(port)), timeout=0.5):
                status_var.set(f"🟢 Conectado a {ip}:{port}")
        except:
            status_var.set(f"🔴 No conectado ({ip}:{port})")

    def escanear_dispositivos(ip_var, port_var):
        def _scan():
            encontrados = escanear_dispositivos_zebra()
            if encontrados:
                ip_var.set(encontrados[0])
                port_var.set("9100")
                actualizar_config()
                actualizar_status(ip_var.get(), port_var.get())
            else:
                status_var.set("🔴 Zebra no encontrada")
                messagebox.showwarning("Zebra no encontrada", "No se encontraron dispositivos Zebra en la red.")
        threading.Thread(target=_scan).start()

    config_menu.add_command(label="Buscar Dispositivos Zebra", command=lambda: escanear_dispositivos(ip_var, port_var))
    config_menu.add_separator()
    config_menu.add_command(label="Guardar Configuración", command=actualizar_config)
    menu_bar.add_cascade(label="Conexión", menu=config_menu)
    root.config(menu=menu_bar)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0)

    campos = {
        "rut": "RUT",
        "razsoc": "Cliente",
        "dir": "Dirección",
        "comuna": "Comuna",
        "ciudad": "Ciudad",
        "guia": "Guía",
        "bultos": "Bultos",
        "transporte": "Transporte"
    }

    entradas = {}
    for idx, (key, label) in enumerate(campos.items()):
        ttk.Label(frame, text=label + ":").grid(row=idx, column=0, sticky="e", pady=5)
        entry = ttk.Entry(frame, width=40)
        entry.grid(row=idx, column=1, pady=5)
        entradas[key] = entry

    fila_base = len(campos)
    ttk.Label(frame, text="Cantidad:").grid(row=fila_base, column=0, sticky="e", pady=5)
    cantidad_spin = tk.Spinbox(frame, from_=1, to=100, width=38)
    cantidad_spin.grid(row=fila_base, column=1, pady=5)

    def cargar_datos_cliente(event=None):
        rut = entradas["rut"].get()
        cliente = buscar_cliente_por_rut(df_clientes, rut)
        if cliente:
            for campo in ["razsoc", "dir", "comuna", "ciudad"]:
                entradas[campo].delete(0, tk.END)
                entradas[campo].insert(0, cliente[campo])
        else:
            messagebox.showerror("RUT no encontrado", "No se encontró el cliente para el RUT ingresado.")

    entradas["rut"].bind("<Return>", cargar_datos_cliente)

    def imprimir():
        data = {k: v.get() for k, v in entradas.items()}
        cantidad = int(cantidad_spin.get())
        ip, port = ip_var.get(), int(port_var.get())
        zpl = generar_zpl_10x10(data)
        imprimir_zebra_zpl(zpl, ip=ip, port=port, cantidad=cantidad)
        actualizar_status(ip, port)

    ttk.Button(frame, text="🖨️ Imprimir Etiqueta", command=imprimir).grid(row=fila_base+1, column=0, columnspan=2, pady=5)
    status_label = ttk.Label(frame, textvariable=status_var, foreground="blue")
    status_label.grid(row=fila_base+2, column=0, columnspan=2, pady=5)

    actualizar_status(ip_var.get(), port_var.get())
    root.mainloop()

# Inicialización directa si se ejecuta como script
if __name__ == "__main__":
    ruta_excel = obtener_ruta_excel()
    df = cargar_clientes(ruta_excel)
    crear_editor_etiqueta(df)
