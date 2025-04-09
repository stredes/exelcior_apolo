import platform

def is_windows() -> bool:
    return platform.system() == "Windows"

def is_linux() -> bool:
    return platform.system() == "Linux"

def imprimir_etiqueta_plataforma(path_etiqueta, impresora):
    """
    Imprime la etiqueta dependiendo del sistema operativo.
    En Windows usa Excel, en Linux usa LibreOffice.
    """
    if is_windows():
        import win32com.client
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        libro = excel.Workbooks.Open(str(path_etiqueta.resolve()))
        libro.PrintOut()
        libro.Close(False)
        excel.Quit()
    elif is_linux():
        import subprocess
        subprocess.run(["libreoffice", "--headless", "--pt", impresora, str(path_etiqueta.resolve())], check=True)
    else:
        raise NotImplementedError("Sistema operativo no soportado para impresión.")
