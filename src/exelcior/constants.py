"""
Constantes globales para Exelcior Apolo.

Este módulo centraliza todas las constantes utilizadas en la aplicación
para evitar valores hardcodeados y facilitar el mantenimiento.
"""

from pathlib import Path
from typing import Dict, List

# Información de la aplicación
APP_NAME = "Exelcior Apolo"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Transformador Inteligente de Excel para Operaciones Logísticas"
APP_AUTHOR = "Gian Lucas San Martín - GCNJ"

# Configuración de la interfaz
GUI_CONFIG = {
    "window_size": "900x800",
    "min_window_size": (800, 600),
    "theme": "clam",
    "font_family": "Segoe UI",
    "font_size": 11,
    "colors": {
        "primary": "#111827",
        "secondary": "#F9FAFB",
        "accent": "#3B82F6",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444"
    }
}

# Configuración de red
NETWORK_CONFIG = {
    "zebra_default_ip": "192.168.0.100",
    "zebra_default_port": 9100,
    "connection_timeout": 5,
    "retry_attempts": 3
}

# Configuración de archivos
FILE_CONFIG = {
    "supported_formats": [".xlsx", ".xls", ".csv", ".xlsm", ".xlsb", ".ods"],
    "max_file_size_mb": 100,
    "backup_retention_days": 30,
    "temp_dir": "temp",
    "exports_dir": "exports",
    "logs_dir": "logs"
}

# Configuración de base de datos
DATABASE_CONFIG = {
    "name": "exelcior.db",
    "backup_name": "exelcior_backup.db",
    "connection_pool_size": 5,
    "echo_sql": False
}

# Configuración de logging
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "max_file_size_mb": 10,
    "backup_count": 5
}

# Configuración de stock
STOCK_CONFIG = {
    "thresholds": {
        "critical": 5,
        "low": 20,
        "high": 50
    },
    "expiration_alert_days": 90,
    "special_fields": ["N° Serie", "Lote"]
}

# Modos de operación
OPERATION_MODES = {
    "fedex": {
        "name": "FedEx",
        "description": "Procesamiento de envíos FedEx",
        "required_columns": ["SHIPDATE", "MASTERTRACKINGNUMBER", "REFERENCE", 
                           "RECIPIENTCITY", "RECIPIENTCONTACTNAME", "PIECETRACKINGNUMBER"],
        "group_by": "MASTERTRACKINGNUMBER",
        "count_column": "PIECETRACKINGNUMBER",
        "display_name": "BULTOS"
    },
    "urbano": {
        "name": "Urbano",
        "description": "Procesamiento de envíos urbanos",
        "required_columns": ["FECHA", "CLIENTE", "CIUDAD", "PIEZAS"],
        "count_column": "PIEZAS",
        "display_name": "PIEZAS"
    },
    "listados": {
        "name": "Listados",
        "description": "Procesamiento de listados comerciales",
        "required_columns": [],
        "flexible": True
    }
}

# Configuración de impresión
PRINT_CONFIG = {
    "default_printer": "URBANO",
    "page_margins": {
        "top": 20,
        "bottom": 20,
        "left": 20,
        "right": 20
    },
    "font_sizes": {
        "title": 14,
        "header": 12,
        "body": 10,
        "footer": 8
    }
}

# Rutas por defecto
DEFAULT_PATHS = {
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "desktop": Path.home() / "Desktop"
}

# Configuración de validación
VALIDATION_CONFIG = {
    "min_rows": 1,
    "max_rows": 50000,
    "min_columns": 1,
    "max_columns": 100,
    "required_encoding": "utf-8"
}

# Mensajes de la aplicación
MESSAGES = {
    "success": {
        "file_loaded": "Archivo cargado exitosamente",
        "export_complete": "Exportación completada",
        "print_complete": "Impresión completada",
        "config_saved": "Configuración guardada"
    },
    "error": {
        "file_not_found": "Archivo no encontrado",
        "invalid_format": "Formato de archivo no válido",
        "processing_failed": "Error al procesar archivo",
        "network_error": "Error de conexión de red",
        "database_error": "Error de base de datos"
    },
    "warning": {
        "large_file": "Archivo muy grande, el procesamiento puede ser lento",
        "missing_columns": "Algunas columnas requeridas no están presentes",
        "config_not_found": "Archivo de configuración no encontrado"
    }
}

# Configuración de exportación
EXPORT_CONFIG = {
    "pdf": {
        "page_size": "A4",
        "orientation": "portrait",
        "margin": 20,
        "font": "Arial",
        "font_size": 10
    },
    "excel": {
        "engine": "openpyxl",
        "index": False,
        "header": True
    }
}

