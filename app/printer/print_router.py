import platform

so = platform.system().lower()

if so == "windows":
    from app.printer.printer import print_document as print_document
elif so == "linux":
    from app.printer.printer_linux import print_document as print_document
else:
    def print_document(*args, **kwargs):
        raise NotImplementedError(f"Sistema operativo no soportado: {so}")
