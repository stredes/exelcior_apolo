from datetime import datetime

def generate_timestamp():
    """Devuelve una marca de tiempo en formato legible."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")