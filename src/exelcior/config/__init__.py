"""
Módulo de configuración para Exelcior Apolo.

Proporciona un sistema centralizado de gestión de configuración
que elimina la duplicación de código y mejora la mantenibilidad.
"""

from .manager import (
    ConfigManager,
    DatabaseConfig,
    NetworkConfig,
    StockConfig,
    UserConfig,
    config_manager
)

__all__ = [
    "ConfigManager",
    "DatabaseConfig", 
    "NetworkConfig",
    "StockConfig",
    "UserConfig",
    "config_manager"
]

