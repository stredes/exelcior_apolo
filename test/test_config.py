from app.config import config_dialog


def test_get_default_config():
    config = config_dialog.get_default_config()

    # Validaciones básicas
    assert isinstance(config, dict)
    assert "fedex" in config
    fedex_config = config["fedex"]
    assert isinstance(fedex_config, dict)

    # Validar claves conocidas
    assert "eliminar" in fedex_config
    assert "mantener_formato" in fedex_config
    assert isinstance(fedex_config["eliminar"], list)
    assert isinstance(fedex_config["mantener_formato"], list)
