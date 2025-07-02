def validate_config_structure(config: dict) -> bool:
    """
    Valida la estructura esperada del archivo de configuración JSON.

    Args:
        config (dict): Diccionario cargado desde el archivo JSON.

    Returns:
        bool: True si la estructura es válida, False si falta algún campo esencial.
    """
    modos_requeridos = {"listados", "fedex", "urbano"}
    for modo in modos_requeridos:
        if modo not in config:
            return False
        if not isinstance(config[modo], dict):
            return False
    return True
