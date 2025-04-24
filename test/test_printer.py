from app.printer import printer_utils

def test_zpl_generation():
    zpl = printer_utils.generate_label("Producto Test", "123456")
    assert "^XA" in zpl  # comando de inicio ZPL
    assert "Producto Test" in zpl
