"""
Procesador de archivos Excel refactorizado para Exelcior Apolo.

Este módulo maneja la carga, validación y transformación de archivos Excel
con una arquitectura limpia y manejo robusto de errores.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union
import pandas as pd
from ..constants import OPERATION_MODES, FILE_CONFIG
from ..utils import (
    get_logger, 
    FileValidator, 
    DataValidator,
    FileProcessingError,
    ValidationError
)

logger = get_logger("exelcior.core.excel")


class ExcelProcessor:
    """
    Procesador principal para archivos Excel.
    
    Maneja la carga, validación y transformación de archivos Excel
    según diferentes modos de operación.
    """

    def __init__(self):
        """Inicializa el procesador de Excel."""
        self.supported_engines = {
            '.xlsx': 'openpyxl',
            '.xlsm': 'openpyxl', 
            '.xltx': 'openpyxl',
            '.xltm': 'openpyxl',
            '.xls': 'xlrd',
            '.xlsb': 'pyxlsb',
            '.ods': 'odf'
        }

    def load_file(
        self, 
        file_path: Union[str, Path], 
        mode: str,
        max_rows: Optional[int] = None,
        start_row: int = 0
    ) -> pd.DataFrame:
        """
        Carga un archivo Excel con validación completa.
        
        Args:
            file_path: Ruta del archivo a cargar
            mode: Modo de operación
            max_rows: Número máximo de filas a cargar
            start_row: Fila desde la cual empezar a leer
            
        Returns:
            DataFrame con los datos cargados
            
        Raises:
            FileProcessingError: Si hay errores en la carga
        """
        try:
            # Validaciones previas
            path = FileValidator.validate_file_path(file_path)
            extension = FileValidator.validate_file_format(path)
            FileValidator.validate_file_size(path)
            
            logger.info(f"Cargando archivo: {path}")
            
            # Determinar engine y cargar archivo
            df = self._load_with_engine(path, extension, max_rows, start_row)
            
            # Validar y normalizar datos
            df = self._normalize_dataframe(df)
            DataValidator.validate_dataframe(df)
            DataValidator.validate_required_columns(df, mode)
            
            logger.info(f"Archivo cargado exitosamente: {df.shape[0]} filas, {df.shape[1]} columnas")
            return df
            
        except ValidationError as e:
            logger.error(f"Error de validación: {e}")
            raise FileProcessingError(f"Error de validación: {e.message}", error_code=e.error_code)
        except Exception as e:
            logger.error(f"Error inesperado al cargar archivo: {e}")
            raise FileProcessingError(f"No se pudo cargar el archivo: {str(e)}")

    def _load_with_engine(
        self, 
        path: Path, 
        extension: str, 
        max_rows: Optional[int],
        start_row: int
    ) -> pd.DataFrame:
        """
        Carga el archivo usando el engine apropiado.
        
        Args:
            path: Ruta del archivo
            extension: Extensión del archivo
            max_rows: Número máximo de filas
            start_row: Fila de inicio
            
        Returns:
            DataFrame cargado
        """
        skiprows = list(range(start_row)) if start_row > 0 else None
        
        if extension == '.csv':
            return pd.read_csv(path, skiprows=skiprows, nrows=max_rows)
        
        engine = self.supported_engines.get(extension)
        if not engine:
            raise FileProcessingError(f"Engine no disponible para {extension}")
        
        try:
            return pd.read_excel(
                path, 
                engine=engine, 
                skiprows=skiprows, 
                nrows=max_rows
            )
        except Exception as e:
            # Intentar con engine alternativo si falla
            if extension == '.xls' and engine == 'xlrd':
                try:
                    return pd.read_excel(path, engine='openpyxl', skiprows=skiprows, nrows=max_rows)
                except:
                    pass
            raise FileProcessingError(f"Error al leer archivo con engine {engine}: {str(e)}")

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza el DataFrame para procesamiento consistente.
        
        Args:
            df: DataFrame a normalizar
            
        Returns:
            DataFrame normalizado
        """
        # Normalizar nombres de columnas
        df.columns = [
            str(col).strip().upper().replace(" ", "_").replace(".", "_")
            for col in df.columns
        ]
        
        # Remover filas completamente vacías
        df = df.dropna(how='all')
        
        # Resetear índice
        df = df.reset_index(drop=True)
        
        return df

    def transform_data(self, df: pd.DataFrame, mode: str) -> Tuple[pd.DataFrame, Optional[float]]:
        """
        Transforma los datos según el modo de operación.
        
        Args:
            df: DataFrame a transformar
            mode: Modo de operación
            
        Returns:
            Tupla con DataFrame transformado y total calculado
            
        Raises:
            FileProcessingError: Si hay errores en la transformación
        """
        try:
            logger.info(f"Transformando datos para modo: {mode}")
            
            if mode not in OPERATION_MODES:
                raise FileProcessingError(f"Modo de operación no válido: {mode}")
            
            transformer = self._get_transformer(mode)
            return transformer(df.copy())
            
        except Exception as e:
            logger.error(f"Error en transformación: {e}")
            raise FileProcessingError(f"Error al transformar datos: {str(e)}")

    def _get_transformer(self, mode: str):
        """Obtiene la función de transformación para un modo específico."""
        transformers = {
            'fedex': self._transform_fedex,
            'urbano': self._transform_urbano,
            'listados': self._transform_listados
        }
        return transformers.get(mode, self._transform_listados)

    def _transform_fedex(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
        """
        Transforma datos para modo FedEx.
        
        Args:
            df: DataFrame a transformar
            
        Returns:
            Tupla con DataFrame agrupado y total de bultos
        """
        required_cols = ["SHIPDATE", "MASTERTRACKINGNUMBER", "REFERENCE", 
                        "RECIPIENTCITY", "RECIPIENTCONTACTNAME", "PIECETRACKINGNUMBER"]
        
        # Verificar columnas requeridas
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise FileProcessingError(f"Faltan columnas para FedEx: {missing_cols}")
        
        # Filtrar filas con tracking number válido
        df_filtered = df[df["MASTERTRACKINGNUMBER"].notna()].copy()
        
        if df_filtered.empty:
            raise FileProcessingError("No hay registros válidos con MASTERTRACKINGNUMBER")
        
        # Agrupar por tracking number
        grouped = (
            df_filtered.groupby("MASTERTRACKINGNUMBER")
            .agg({
                "SHIPDATE": "first",
                "REFERENCE": "first", 
                "RECIPIENTCITY": "first",
                "RECIPIENTCONTACTNAME": "first",
                "PIECETRACKINGNUMBER": "count"
            })
            .reset_index()
        )
        
        # Renombrar columnas para presentación
        grouped.columns = [
            "Tracking_Number", "Fecha", "Referencia", 
            "Ciudad", "Receptor", "BULTOS"
        ]
        
        total_bultos = float(grouped["BULTOS"].sum())
        
        logger.info(f"FedEx: {len(grouped)} registros agrupados, {total_bultos} bultos totales")
        return grouped, total_bultos

    def _transform_urbano(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
        """
        Transforma datos para modo Urbano.
        
        Args:
            df: DataFrame a transformar
            
        Returns:
            Tupla con DataFrame procesado y total de piezas
        """
        required_cols = ["FECHA", "CLIENTE", "CIUDAD", "PIEZAS"]
        
        # Verificar columnas requeridas
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise FileProcessingError(f"Faltan columnas para Urbano: {missing_cols}")
        
        # Filtrar registros válidos
        df_filtered = df[
            df["CLIENTE"].notna() & 
            df["PIEZAS"].notna()
        ].copy()
        
        if df_filtered.empty:
            raise FileProcessingError("No hay registros válidos para modo Urbano")
        
        # Convertir PIEZAS a numérico
        try:
            df_filtered["PIEZAS"] = pd.to_numeric(df_filtered["PIEZAS"], errors='coerce')
            df_filtered = df_filtered[df_filtered["PIEZAS"].notna()]
        except Exception as e:
            raise FileProcessingError(f"Error al procesar columna PIEZAS: {str(e)}")
        
        total_piezas = float(df_filtered["PIEZAS"].sum())
        
        logger.info(f"Urbano: {len(df_filtered)} registros, {total_piezas} piezas totales")
        return df_filtered, total_piezas

    def _transform_listados(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, None]:
        """
        Transforma datos para modo Listados (procesamiento general).
        
        Args:
            df: DataFrame a transformar
            
        Returns:
            Tupla con DataFrame sin modificaciones y None como total
        """
        logger.info(f"Listados: {len(df)} registros procesados")
        return df, None

    def remove_duplicates(self, df: pd.DataFrame, reference_column: str = "REFERENCE") -> pd.DataFrame:
        """
        Remueve duplicados basado en una columna de referencia.
        
        Args:
            df: DataFrame a procesar
            reference_column: Columna para identificar duplicados
            
        Returns:
            DataFrame sin duplicados
        """
        if reference_column not in df.columns:
            logger.warning(f"Columna {reference_column} no encontrada, no se removieron duplicados")
            return df
        
        initial_count = len(df)
        df_unique = df.drop_duplicates(subset=[reference_column], keep='first')
        final_count = len(df_unique)
        
        removed_count = initial_count - final_count
        if removed_count > 0:
            logger.info(f"Removidos {removed_count} duplicados basados en {reference_column}")
        
        return df_unique

    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Obtiene información básica de un archivo.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Diccionario con información del archivo
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            return {
                "name": path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
                "extension": path.suffix.lower(),
                "is_supported": path.suffix.lower() in FILE_CONFIG["supported_formats"]
            }
        except Exception as e:
            logger.error(f"Error al obtener información del archivo: {e}")
            return {}


# Instancia global del procesador
excel_processor = ExcelProcessor()

