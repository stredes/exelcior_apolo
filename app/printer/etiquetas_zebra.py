# app/printer/etiquetas_zebra.py
import json
import socket
from pathlib import Path
from tkinter import messagebox


def cargar_configuracion():
    config_path = Path("config.json")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def imprimir_zebra_zpl(zpl: str, ip: str, port: int, cantidad: int = 1):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            for _ in range(cantidad):
                s.sendall(zpl.encode("utf-8"))
        messagebox.showinfo(
            "Impresión enviada", f"{cantidad} etiqueta(s) enviada(s) a {ip}:{port}"
        )
    except Exception as e:
        messagebox.showerror("Error en impresión", f"No se pudo imprimir: {e}")


def generar_zpl(data: dict) -> str:
    return f"""^XA
^PW800
^LL800
^CF0,40
^FO50,30^FD{data['razsoc']}^FS
^FO50,100^FD{data['dir']}^FS
^FO50,150^FD{data['comuna']}^FS
^FO50,200^FD{data['ciudad']}^FS
^FO50,250^FDGuía: {data['guia']}^FS
^FO50,300^FDDespacho: {data['transporte']}^FS
^FO50,350^FDBULTO: {data['bultos']}^FS
^FO50,420^BCN,100,Y,N,N
^FD{data['guia']}^FS
^XZ"""


def imprimir_etiqueta_desde_datos(data: dict):
    config = cargar_configuracion()
    ip = config.get("zebra_ip", "192.168.0.100")
    port = config.get("zebra_port", 9100)
    zpl = generar_zpl(data)
    imprimir_zebra_zpl(zpl, ip, port, cantidad=1)
