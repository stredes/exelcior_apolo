def generate_label(nombre, codigo):
    """Genera una etiqueta ZPL simple con nombre y código."""
    return f"^XA\n^FO50,50^ADN,36,20^FD{nombre} - {codigo}^FS\n^XZ"
