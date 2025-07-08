# app/utils/utils.py

"""
Módulo de utilidades generales del sistema.
Las funciones de configuración fueron trasladadas a app/config/config_manager.py
para evitar duplicación y mejorar la arquitectura.
"""

# 🔄 Delegación explícita a la fuente única de configuración
from app.config.config_manager import (
    load_config,
    save_config,
    guardar_ultimo_path
)

# Aquí puedes mantener o agregar otras utilidades generales no relacionadas con configuración.
