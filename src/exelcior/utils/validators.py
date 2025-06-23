"""
Sistema de validación centralizado para Exelcior Apolo.

Proporciona validadores reutilizables para diferentes tipos de datos
y operaciones de la aplicación.
"""

import re
from pathlib import Path
from typing import List, Optional, Union, Any
import pandas as pd
from ..constants import FILE_CONFIG, VALIDATION_CONFIG, OPERATION_MODES
from .exceptions import ValidationError


class FileValidator:
    """Validador para archivos y operaciones relacionadas."""

    @staticmethod
    def validate_file_path(file_path: Union[str, Path]) -> Path:
        """
        Valida que un archivo existe y es accesible.
        
        Args:
            file_path: Ruta del archivo a validar
            
        Returns:
            Path object validado
            
        Raises:
            ValidationError: Si el archivo no es válido
        """
        path = Path(file_path)
        
        if not path.exists():
            raise ValidationError(
                f"El archivo no existe: {path}",
                error_code="FILE_NOT_FOUND"
            )
        
        if not path.is_file():
            raise ValidationError(
                f"La ruta no corresponde a un archivo: {path}",
                error_code="NOT_A_FILE"
            )
        
        if not path.stat().st_size > 0:
            raise ValidationError(
                f"El archivo está vacío: {path}",
                error_code="EMPTY_FILE"
            )
        
        return path

    @staticmethod
    def validate_file_format(file_path: Union[str, Path]) -> str:
        """
        Valida que el formato del archivo es soportado.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Extensión del archivo
            
        Raises:
            ValidationError: Si el formato no es soportado
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension not in FILE_CONFIG["supported_formats"]:
            raise ValidationError(
                f"Formato de archivo no soportado: {extension}. "
                f"Formatos válidos: {', '.join(FILE_CONFIG['supported_formats'])}",
                error_code="UNSUPPORTED_FORMAT"
            )
        
        return extension

    @staticmethod
    def validate_file_size(file_path: Union[str, Path]) -> int:
        """
        Valida que el tamaño del archivo está dentro de los límites.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Tamaño del archivo en bytes
            
        Raises:
            ValidationError: Si el archivo es demasiado grande
        """
        path = Path(file_path)
        size_bytes = path.stat().st_size
        max_size_bytes = FILE_CONFIG["max_file_size_mb"] * 1024 * 1024
        
        if size_bytes > max_size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            raise ValidationError(
                f"El archivo es demasiado grande: {size_mb:.1f}MB. "
                f"Tamaño máximo: {FILE_CONFIG['max_file_size_mb']}MB",
                error_code="FILE_TOO_LARGE"
            )
        
        return size_bytes


class DataValidator:
    """Validador para datos y DataFrames."""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Valida que un DataFrame cumple con los requisitos básicos.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            DataFrame validado
            
        Raises:
            ValidationError: Si el DataFrame no es válido
        """
        if df is None:
            raise ValidationError(
                "DataFrame no puede ser None",
                error_code="NULL_DATAFRAME"
            )
        
        if df.empty:
            raise ValidationError(
                "DataFrame no puede estar vacío",
                error_code="EMPTY_DATAFRAME"
            )
        
        rows, cols = df.shape
        
        if rows < VALIDATION_CONFIG["min_rows"]:
            raise ValidationError(
                f"DataFrame debe tener al menos {VALIDATION_CONFIG['min_rows']} filas. "
                f"Actual: {rows}",
                error_code="INSUFFICIENT_ROWS"
            )
        
        if rows > VALIDATION_CONFIG["max_rows"]:
            raise ValidationError(
                f"DataFrame tiene demasiadas filas: {rows}. "
                f"Máximo: {VALIDATION_CONFIG['max_rows']}",
                error_code="TOO_MANY_ROWS"
            )
        
        if cols < VALIDATION_CONFIG["min_columns"]:
            raise ValidationError(
                f"DataFrame debe tener al menos {VALIDATION_CONFIG['min_columns']} columnas. "
                f"Actual: {cols}",
                error_code="INSUFFICIENT_COLUMNS"
            )
        
        if cols > VALIDATION_CONFIG["max_columns"]:
            raise ValidationError(
                f"DataFrame tiene demasiadas columnas: {cols}. "
                f"Máximo: {VALIDATION_CONFIG['max_columns']}",
                error_code="TOO_MANY_COLUMNS"
            )
        
        return df

    @staticmethod
    def validate_required_columns(df: pd.DataFrame, mode: str) -> List[str]:
        """
        Valida que el DataFrame tiene las columnas requeridas para un modo.
        
        Args:
            df: DataFrame a validar
            mode: Modo de operación
            
        Returns:
            Lista de columnas requeridas encontradas
            
        Raises:
            ValidationError: Si faltan columnas requeridas
        """
        if mode not in OPERATION_MODES:
            raise ValidationError(
                f"Modo de operación no válido: {mode}",
                error_code="INVALID_MODE"
            )
        
        mode_config = OPERATION_MODES[mode]
        required_columns = mode_config.get("required_columns", [])
        
        if not required_columns:  # Modo flexible
            return list(df.columns)
        
        # Normalizar nombres de columnas para comparación
        df_columns_normalized = [col.strip().upper().replace(" ", "_") for col in df.columns]
        required_normalized = [col.strip().upper().replace(" ", "_") for col in required_columns]
        
        missing_columns = []
        for req_col in required_normalized:
            if req_col not in df_columns_normalized:
                missing_columns.append(req_col)
        
        if missing_columns:
            raise ValidationError(
                f"Faltan columnas requeridas para modo {mode}: {', '.join(missing_columns)}",
                error_code="MISSING_REQUIRED_COLUMNS",
                details={"missing": missing_columns, "available": list(df.columns)}
            )
        
        return required_columns


class NetworkValidator:
    """Validador para configuraciones de red."""

    @staticmethod
    def validate_ip_address(ip: str) -> str:
        """
        Valida que una dirección IP es válida.
        
        Args:
            ip: Dirección IP a validar
            
        Returns:
            IP validada
            
        Raises:
            ValidationError: Si la IP no es válida
        """
        ip_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        
        if not ip_pattern.match(ip):
            raise ValidationError(
                f"Dirección IP no válida: {ip}",
                error_code="INVALID_IP"
            )
        
        return ip

    @staticmethod
    def validate_port(port: Union[int, str]) -> int:
        """
        Valida que un puerto es válido.
        
        Args:
            port: Puerto a validar
            
        Returns:
            Puerto validado como entero
            
        Raises:
            ValidationError: Si el puerto no es válido
        """
        try:
            port_int = int(port)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Puerto debe ser un número entero: {port}",
                error_code="INVALID_PORT_TYPE"
            )
        
        if not (1 <= port_int <= 65535):
            raise ValidationError(
                f"Puerto debe estar entre 1 y 65535: {port_int}",
                error_code="INVALID_PORT_RANGE"
            )
        
        return port_int


class ConfigValidator:
    """Validador para configuraciones."""

    @staticmethod
    def validate_mode(mode: str) -> str:
        """
        Valida que un modo de operación es válido.
        
        Args:
            mode: Modo a validar
            
        Returns:
            Modo validado
            
        Raises:
            ValidationError: Si el modo no es válido
        """
        if mode not in OPERATION_MODES:
            valid_modes = list(OPERATION_MODES.keys())
            raise ValidationError(
                f"Modo de operación no válido: {mode}. "
                f"Modos válidos: {', '.join(valid_modes)}",
                error_code="INVALID_MODE"
            )
        
        return mode

    @staticmethod
    def validate_threshold_values(critical: int, low: int, high: int) -> tuple:
        """
        Valida que los umbrales de stock son lógicos.
        
        Args:
            critical: Umbral crítico
            low: Umbral bajo
            high: Umbral alto
            
        Returns:
            Tupla de umbrales validados
            
        Raises:
            ValidationError: Si los umbrales no son lógicos
        """
        if not (critical < low < high):
            raise ValidationError(
                f"Los umbrales deben cumplir: crítico < bajo < alto. "
                f"Actual: {critical} < {low} < {high}",
                error_code="INVALID_THRESHOLDS"
            )
        
        if critical < 0:
            raise ValidationError(
                f"El umbral crítico no puede ser negativo: {critical}",
                error_code="NEGATIVE_THRESHOLD"
            )
        
        return critical, low, high

