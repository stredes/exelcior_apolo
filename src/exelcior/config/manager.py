"""
Sistema de configuración centralizado para Exelcior Apolo.

Este módulo maneja toda la configuración de la aplicación de manera centralizada,
eliminando la duplicación de código y proporcionando una interfaz consistente.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from ..constants import DATABASE_CONFIG, NETWORK_CONFIG, STOCK_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuración de base de datos."""
    name: str = DATABASE_CONFIG["name"]
    backup_name: str = DATABASE_CONFIG["backup_name"]
    connection_pool_size: int = DATABASE_CONFIG["connection_pool_size"]
    echo_sql: bool = DATABASE_CONFIG["echo_sql"]


@dataclass
class NetworkConfig:
    """Configuración de red."""
    zebra_ip: str = NETWORK_CONFIG["zebra_default_ip"]
    zebra_port: int = NETWORK_CONFIG["zebra_default_port"]
    connection_timeout: int = NETWORK_CONFIG["connection_timeout"]
    retry_attempts: int = NETWORK_CONFIG["retry_attempts"]


@dataclass
class StockConfig:
    """Configuración de stock."""
    critical_threshold: int = STOCK_CONFIG["thresholds"]["critical"]
    low_threshold: int = STOCK_CONFIG["thresholds"]["low"]
    high_threshold: int = STOCK_CONFIG["thresholds"]["high"]
    expiration_alert_days: int = STOCK_CONFIG["expiration_alert_days"]
    special_fields: list = None

    def __post_init__(self):
        if self.special_fields is None:
            self.special_fields = STOCK_CONFIG["special_fields"].copy()


@dataclass
class UserConfig:
    """Configuración específica del usuario."""
    default_mode: str = "listados"
    default_printer: str = "URBANO"
    auto_load_enabled: bool = True
    custom_download_paths: Dict[str, str] = None
    recent_files: list = None

    def __post_init__(self):
        if self.custom_download_paths is None:
            self.custom_download_paths = {}
        if self.recent_files is None:
            self.recent_files = []


class ConfigManager:
    """
    Gestor centralizado de configuración.
    
    Maneja la carga, guardado y acceso a todas las configuraciones
    de la aplicación de manera thread-safe y consistente.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Inicializa el gestor de configuración.
        
        Args:
            config_dir: Directorio donde almacenar archivos de configuración.
                       Si es None, usa el directorio actual.
        """
        self.config_dir = config_dir or Path("config")
        self.config_dir.mkdir(exist_ok=True)
        
        self._database_config = DatabaseConfig()
        self._network_config = NetworkConfig()
        self._stock_config = StockConfig()
        self._user_config = UserConfig()
        
        self._config_files = {
            "database": self.config_dir / "database.json",
            "network": self.config_dir / "network.json",
            "stock": self.config_dir / "stock.json",
            "user": self.config_dir / "user.json"
        }
        
        self.load_all_configs()

    @property
    def database(self) -> DatabaseConfig:
        """Acceso a configuración de base de datos."""
        return self._database_config

    @property
    def network(self) -> NetworkConfig:
        """Acceso a configuración de red."""
        return self._network_config

    @property
    def stock(self) -> StockConfig:
        """Acceso a configuración de stock."""
        return self._stock_config

    @property
    def user(self) -> UserConfig:
        """Acceso a configuración de usuario."""
        return self._user_config

    def load_all_configs(self) -> None:
        """Carga todas las configuraciones desde archivos."""
        try:
            self._database_config = self._load_config("database", DatabaseConfig)
            self._network_config = self._load_config("network", NetworkConfig)
            self._stock_config = self._load_config("stock", StockConfig)
            self._user_config = self._load_config("user", UserConfig)
            logger.info("Configuraciones cargadas exitosamente")
        except Exception as e:
            logger.error(f"Error al cargar configuraciones: {e}")

    def save_all_configs(self) -> None:
        """Guarda todas las configuraciones a archivos."""
        try:
            self._save_config("database", self._database_config)
            self._save_config("network", self._network_config)
            self._save_config("stock", self._stock_config)
            self._save_config("user", self._user_config)
            logger.info("Configuraciones guardadas exitosamente")
        except Exception as e:
            logger.error(f"Error al guardar configuraciones: {e}")

    def _load_config(self, config_name: str, config_class: type) -> Any:
        """
        Carga una configuración específica desde archivo.
        
        Args:
            config_name: Nombre de la configuración
            config_class: Clase de configuración a instanciar
            
        Returns:
            Instancia de la configuración cargada
        """
        config_file = self._config_files[config_name]
        
        if not config_file.exists():
            logger.warning(f"Archivo de configuración {config_name} no encontrado, usando valores por defecto")
            return config_class()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return config_class(**data)
        except Exception as e:
            logger.error(f"Error al cargar configuración {config_name}: {e}")
            return config_class()

    def _save_config(self, config_name: str, config_obj: Any) -> None:
        """
        Guarda una configuración específica a archivo.
        
        Args:
            config_name: Nombre de la configuración
            config_obj: Objeto de configuración a guardar
        """
        config_file = self._config_files[config_name]
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config_obj), f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error al guardar configuración {config_name}: {e}")

    def update_database_config(self, **kwargs) -> None:
        """Actualiza configuración de base de datos."""
        for key, value in kwargs.items():
            if hasattr(self._database_config, key):
                setattr(self._database_config, key, value)
        self._save_config("database", self._database_config)

    def update_network_config(self, **kwargs) -> None:
        """Actualiza configuración de red."""
        for key, value in kwargs.items():
            if hasattr(self._network_config, key):
                setattr(self._network_config, key, value)
        self._save_config("network", self._network_config)

    def update_stock_config(self, **kwargs) -> None:
        """Actualiza configuración de stock."""
        for key, value in kwargs.items():
            if hasattr(self._stock_config, key):
                setattr(self._stock_config, key, value)
        self._save_config("stock", self._stock_config)

    def update_user_config(self, **kwargs) -> None:
        """Actualiza configuración de usuario."""
        for key, value in kwargs.items():
            if hasattr(self._user_config, key):
                setattr(self._user_config, key, value)
        self._save_config("user", self._user_config)

    def get_download_path(self, mode: str) -> Path:
        """
        Obtiene la ruta de descarga para un modo específico.
        
        Args:
            mode: Modo de operación
            
        Returns:
            Ruta de descarga configurada o por defecto
        """
        custom_path = self._user_config.custom_download_paths.get(mode)
        if custom_path and Path(custom_path).exists():
            return Path(custom_path)
        return Path.home() / "Downloads"

    def set_download_path(self, mode: str, path: Union[str, Path]) -> None:
        """
        Establece la ruta de descarga para un modo específico.
        
        Args:
            mode: Modo de operación
            path: Nueva ruta de descarga
        """
        self._user_config.custom_download_paths[mode] = str(path)
        self._save_config("user", self._user_config)

    def add_recent_file(self, file_path: str, mode: str) -> None:
        """
        Añade un archivo a la lista de archivos recientes.
        
        Args:
            file_path: Ruta del archivo
            mode: Modo de operación utilizado
        """
        recent_entry = {
            "path": file_path,
            "mode": mode,
            "timestamp": str(Path(file_path).stat().st_mtime)
        }
        
        # Remover entrada existente si existe
        self._user_config.recent_files = [
            f for f in self._user_config.recent_files 
            if f.get("path") != file_path
        ]
        
        # Añadir al inicio y limitar a 10 archivos
        self._user_config.recent_files.insert(0, recent_entry)
        self._user_config.recent_files = self._user_config.recent_files[:10]
        
        self._save_config("user", self._user_config)

    def get_recent_files(self) -> list:
        """Obtiene la lista de archivos recientes."""
        return self._user_config.recent_files.copy()

    def reset_to_defaults(self, config_type: Optional[str] = None) -> None:
        """
        Resetea configuraciones a valores por defecto.
        
        Args:
            config_type: Tipo específico de configuración a resetear.
                        Si es None, resetea todas.
        """
        if config_type is None or config_type == "database":
            self._database_config = DatabaseConfig()
        if config_type is None or config_type == "network":
            self._network_config = NetworkConfig()
        if config_type is None or config_type == "stock":
            self._stock_config = StockConfig()
        if config_type is None or config_type == "user":
            self._user_config = UserConfig()
        
        if config_type is None:
            self.save_all_configs()
        else:
            self._save_config(config_type, getattr(self, f"_{config_type}_config"))


# Instancia global del gestor de configuración
config_manager = ConfigManager()

