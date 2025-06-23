"""
Sistema de detección y manejo de códigos Urbano de 9 dígitos.

Detecta automáticamente archivos de Urbano basándose en el nombre del archivo
y aplica configuraciones específicas para el procesamiento.
"""

import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd

from ..utils import get_logger, FileProcessingError

logger = get_logger("exelcior.core.urbano_detector")


class UrbanoCodeDetector:
    """
    Detector de códigos internos de Urbano.
    
    Identifica archivos de Urbano basándose en patrones de nombres
    y aplica configuraciones específicas para su procesamiento.
    """

    # Patrón para códigos de 9 dígitos
    URBANO_CODE_PATTERN = re.compile(r'^\d{9}$')
    
    # Patrones adicionales para archivos Urbano
    URBANO_FILE_PATTERNS = [
        re.compile(r'^\d{9}\.xlsx?$'),  # 192403809.xlsx
        re.compile(r'urbano_\d{9}\.xlsx?$'),  # urbano_192403809.xlsx
        re.compile(r'WYB\d+\.xlsx?$'),  # Archivos con códigos WYB
        re.compile(r'.*urbano.*\.xlsx?$', re.IGNORECASE),  # Cualquier archivo con "urbano"
    ]

    @classmethod
    def is_urbano_file(cls, file_path: Path) -> bool:
        """
        Determina si un archivo es de tipo Urbano.
        
        Args:
            file_path: Ruta del archivo a verificar
            
        Returns:
            True si es archivo Urbano, False en caso contrario
        """
        try:
            filename = file_path.name
            
            # Verificar patrón de 9 dígitos (PRIORIDAD MÁXIMA)
            name_without_ext = file_path.stem
            if cls.URBANO_CODE_PATTERN.match(name_without_ext):
                logger.info(f"Archivo Urbano detectado por código de 9 dígitos: {filename}")
                return True
            
            # Verificar otros patrones
            for pattern in cls.URBANO_FILE_PATTERNS:
                if pattern.match(filename):
                    logger.info(f"Archivo Urbano detectado por patrón: {filename}")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error detectando tipo Urbano: {e}")
            return False

    @classmethod
    def extract_urbano_code(cls, file_path: Path) -> Optional[str]:
        """
        Extrae el código Urbano del nombre del archivo.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Código Urbano de 9 dígitos o None si no se encuentra
        """
        try:
            filename = file_path.stem
            
            # Buscar código de 9 dígitos
            if cls.URBANO_CODE_PATTERN.match(filename):
                return filename
            
            # Buscar código en el nombre del archivo
            match = re.search(r'\d{9}', filename)
            if match:
                return match.group()
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extrayendo código Urbano: {e}")
            return None

    @classmethod
    def detect_urbano_structure(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detecta la estructura específica de archivos Urbano.
        
        Args:
            df: DataFrame cargado del archivo
            
        Returns:
            Diccionario con información de la estructura detectada
        """
        try:
            structure_info = {
                "is_urbano": True,  # Si llegamos aquí, ya sabemos que es Urbano por el nombre
                "header_row": 0,
                "data_start_row": 1,
                "expected_columns": [],
                "numeric_columns": [],
                "total_rows": len(df),
                "confidence": 1.0,  # Confianza máxima por detección de nombre
                "mode": "urbano"
            }
            
            # Buscar fila de encabezados típicos de Urbano
            urbano_headers = [
                "GUIA", "SHIPPER", "SERVICIO", "ESTADO", "CLIENTE", 
                "AGENCIA", "LOCALIDAD", "PIEZAS", "PESO", "FECHA CHK", 
                "DIAS", "COD RASTREO"
            ]
            
            # También aceptar variaciones comunes
            header_variations = {
                "GUIA": ["GUIA", "GUÍA", "NUMERO_GUIA", "NUM_GUIA"],
                "CLIENTE": ["CLIENTE", "DESTINATARIO", "RECEPTOR"],
                "LOCALIDAD": ["LOCALIDAD", "CIUDAD", "DESTINO"],
                "PIEZAS": ["PIEZAS", "CANTIDAD", "QTY", "BULTOS"],
                "COD RASTREO": ["COD RASTREO", "CODIGO_RASTREO", "TRACKING"]
            }
            
            # Obtener columnas actuales del DataFrame
            current_columns = [str(col).upper().strip() for col in df.columns]
            
            # Mapear columnas encontradas
            mapped_columns = {}
            for standard_name, variations in header_variations.items():
                for variation in variations:
                    if variation in current_columns:
                        mapped_columns[standard_name] = variation
                        break
            
            # Si no encontramos columnas estándar, usar las que están disponibles
            if not mapped_columns and len(current_columns) > 0:
                # Asumir estructura básica basada en posición
                if len(current_columns) >= 4:
                    structure_info["expected_columns"] = current_columns[:6]  # Primeras 6 columnas
                    structure_info["numeric_columns"] = [current_columns[3]] if len(current_columns) > 3 else []
                else:
                    structure_info["expected_columns"] = current_columns
            else:
                structure_info["expected_columns"] = list(mapped_columns.keys())
                structure_info["numeric_columns"] = ["PIEZAS"] if "PIEZAS" in mapped_columns else []
            
            logger.info(f"Estructura Urbano detectada: {len(current_columns)} columnas, {len(df)} filas")
            
            return structure_info
            
        except Exception as e:
            logger.error(f"Error detectando estructura Urbano: {e}")
            return {
                "is_urbano": True,  # Mantener como Urbano por el nombre del archivo
                "header_row": 0,
                "data_start_row": 3,
                "expected_columns": [],
                "numeric_columns": [],
                "total_rows": len(df) if df is not None else 0,
                "confidence": 0.8,  # Confianza alta por nombre, baja por estructura
                "mode": "urbano",
                "error": str(e)
            }

    @classmethod
    def validate_urbano_data(cls, df: pd.DataFrame, structure_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos de un archivo Urbano.
        
        Args:
            df: DataFrame con los datos
            structure_info: Información de estructura detectada
            
        Returns:
            Diccionario con resultado de validación
        """
        try:
            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "total_records": len(df),
                "valid_records": 0,
                "mode": "urbano"
            }
            
            # Validaciones básicas para archivos Urbano
            if len(df) == 0:
                validation_result["errors"].append("El archivo está vacío")
                validation_result["is_valid"] = False
                return validation_result
            
            # Contar registros válidos (filas que no están completamente vacías)
            valid_records = 0
            for idx, row in df.iterrows():
                if not row.isna().all():
                    valid_records += 1
            
            validation_result["valid_records"] = valid_records
            
            # Validaciones específicas
            if valid_records == 0:
                validation_result["warnings"].append("No se encontraron registros válidos")
            elif valid_records < len(df) * 0.5:
                validation_result["warnings"].append(f"Solo {valid_records} de {len(df)} registros parecen válidos")
            
            # Validar columnas numéricas si están disponibles
            numeric_columns = structure_info.get("numeric_columns", [])
            for col in numeric_columns:
                if col in df.columns:
                    try:
                        pd.to_numeric(df[col], errors='coerce')
                    except Exception:
                        validation_result["warnings"].append(f"Columna {col} contiene valores no numéricos")
            
            logger.info(f"Validación Urbano completada: {valid_records} registros válidos de {len(df)}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validando datos Urbano: {e}")
            return {
                "is_valid": False,
                "errors": [f"Error en validación: {str(e)}"],
                "warnings": [],
                "total_records": len(df) if df is not None else 0,
                "valid_records": 0,
                "mode": "urbano"
            }

    @classmethod
    def process_urbano_file(cls, file_path: Path) -> Dict[str, Any]:
        """
        Procesa completamente un archivo Urbano.
        
        Args:
            file_path: Ruta del archivo Urbano
            
        Returns:
            Diccionario con resultado del procesamiento
        """
        try:
            logger.info(f"Procesando archivo Urbano: {file_path.name}")
            
            # Extraer código
            urbano_code = cls.extract_urbano_code(file_path)
            
            # Cargar archivo
            df = pd.read_excel(file_path)
            
            # Detectar estructura
            structure_info = cls.detect_urbano_structure(df)
            
            # Validar datos
            validation_result = cls.validate_urbano_data(df, structure_info)
            
            # Resultado completo
            result = {
                "success": True,
                "file_type": "urbano",
                "urbano_code": urbano_code,
                "file_name": file_path.name,
                "file_path": str(file_path),
                "dataframe": df,
                "structure": structure_info,
                "validation": validation_result,
                "rows": len(df),
                "columns": list(df.columns),
                "mode": "urbano"
            }
            
            logger.info(f"Archivo Urbano procesado exitosamente: {urbano_code}")
            return result
            
        except Exception as e:
            logger.error(f"Error procesando archivo Urbano: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_type": "urbano",
                "file_name": file_path.name if file_path else "unknown",
                "mode": "urbano"
            }


            
        except Exception as e:
            logger.error(f"Error detectando estructura Urbano: {e}")
            return {"is_urbano": False, "confidence": 0.0}

    @classmethod
    def load_urbano_file(cls, file_path: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Carga un archivo Urbano con configuraciones específicas.
        
        Args:
            file_path: Ruta del archivo Urbano
            
        Returns:
            Tupla con DataFrame y metadatos de carga
        """
        try:
            logger.info(f"Cargando archivo Urbano: {file_path.name}")
            
            # Cargar archivo inicial para detectar estructura
            df_raw = pd.read_excel(file_path)
            structure = cls.detect_urbano_structure(df_raw)
            
            if not structure["is_urbano"]:
                raise FileProcessingError(
                    f"El archivo no tiene estructura Urbano válida",
                    "INVALID_URBANO_STRUCTURE"
                )
            
            # Cargar con configuración específica
            header_row = structure["header_row"]
            df = pd.read_excel(file_path, header=header_row)
            
            # Limpiar datos
            df = cls._clean_urbano_data(df, structure)
            
            # Extraer código Urbano
            urbano_code = cls.extract_urbano_code(file_path)
            
            # Metadatos
            metadata = {
                "urbano_code": urbano_code,
                "file_type": "urbano",
                "structure": structure,
                "original_rows": len(df_raw),
                "processed_rows": len(df),
                "columns": list(df.columns),
                "numeric_columns": structure["numeric_columns"]
            }
            
            logger.info(f"Archivo Urbano cargado: {len(df)} filas, código {urbano_code}")
            
            return df, metadata
            
        except Exception as e:
            logger.error(f"Error cargando archivo Urbano: {e}")
            raise FileProcessingError(
                f"Error al cargar archivo Urbano: {str(e)}",
                "URBANO_LOAD_ERROR"
            )

    @classmethod
    def _clean_urbano_data(cls, df: pd.DataFrame, structure: Dict[str, Any]) -> pd.DataFrame:
        """
        Limpia y normaliza datos de archivo Urbano.
        
        Args:
            df: DataFrame a limpiar
            structure: Información de estructura detectada
            
        Returns:
            DataFrame limpio
        """
        try:
            # Eliminar filas completamente vacías
            df = df.dropna(how='all')
            
            # Normalizar nombres de columnas
            df.columns = df.columns.astype(str).str.strip().str.upper()
            
            # Convertir columnas numéricas
            numeric_columns = structure.get("numeric_columns", [])
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Limpiar columnas de texto
            text_columns = [col for col in df.columns if col not in numeric_columns]
            for col in text_columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].replace(['nan', 'None', ''], pd.NA)
            
            # Eliminar filas donde todas las columnas importantes son NaN
            important_cols = ["GUIA", "CLIENTE", "LOCALIDAD"]
            available_important = [col for col in important_cols if col in df.columns]
            if available_important:
                df = df.dropna(subset=available_important, how='all')
            
            logger.info(f"Datos Urbano limpiados: {len(df)} filas válidas")
            
            return df
            
        except Exception as e:
            logger.warning(f"Error limpiando datos Urbano: {e}")
            return df

    @classmethod
    def calculate_urbano_totals(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula totales específicos para archivos Urbano.
        
        Args:
            df: DataFrame con datos Urbano
            
        Returns:
            Diccionario con totales calculados
        """
        try:
            totals = {
                "total_guias": 0,
                "total_piezas": 0,
                "total_peso": 0,
                "total_clientes": 0,
                "localidades": {},
                "estados": {}
            }
            
            # Total de guías
            if "GUIA" in df.columns:
                totals["total_guias"] = df["GUIA"].nunique()
            
            # Total de piezas
            if "PIEZAS" in df.columns:
                piezas_numeric = pd.to_numeric(df["PIEZAS"], errors='coerce')
                totals["total_piezas"] = int(piezas_numeric.sum())
            
            # Total de peso
            if "PESO" in df.columns:
                peso_numeric = pd.to_numeric(df["PESO"], errors='coerce')
                totals["total_peso"] = float(peso_numeric.sum())
            
            # Total de clientes únicos
            if "CLIENTE" in df.columns:
                totals["total_clientes"] = df["CLIENTE"].nunique()
            
            # Distribución por localidad
            if "LOCALIDAD" in df.columns:
                localidad_counts = df["LOCALIDAD"].value_counts().to_dict()
                totals["localidades"] = localidad_counts
            
            # Distribución por estado
            if "ESTADO" in df.columns:
                estado_counts = df["ESTADO"].value_counts().to_dict()
                totals["estados"] = estado_counts
            
            logger.info(f"Totales Urbano calculados: {totals['total_piezas']} piezas, {totals['total_guias']} guías")
            
            return totals
            
        except Exception as e:
            logger.error(f"Error calculando totales Urbano: {e}")
            return {"error": str(e)}

    @classmethod
    def validate_urbano_data(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Valida datos de archivo Urbano.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Diccionario con resultados de validación
        """
        try:
            validation = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "missing_columns": [],
                "empty_required_fields": []
            }
            
            # Columnas requeridas para Urbano
            required_columns = ["GUIA", "CLIENTE", "LOCALIDAD", "PIEZAS"]
            
            # Verificar columnas requeridas
            for col in required_columns:
                if col not in df.columns:
                    validation["missing_columns"].append(col)
                    validation["errors"].append(f"Columna requerida faltante: {col}")
            
            # Verificar campos vacíos en columnas importantes
            for col in required_columns:
                if col in df.columns:
                    empty_count = df[col].isna().sum()
                    if empty_count > 0:
                        validation["empty_required_fields"].append({
                            "column": col,
                            "empty_count": empty_count,
                            "percentage": (empty_count / len(df)) * 100
                        })
                        
                        if empty_count / len(df) > 0.1:  # Más del 10% vacío
                            validation["warnings"].append(
                                f"Columna {col} tiene {empty_count} campos vacíos ({empty_count/len(df)*100:.1f}%)"
                            )
            
            # Validar formato de códigos de guía
            if "GUIA" in df.columns:
                invalid_guias = df[df["GUIA"].astype(str).str.len() < 5]
                if len(invalid_guias) > 0:
                    validation["warnings"].append(
                        f"{len(invalid_guias)} guías con formato posiblemente inválido"
                    )
            
            # Validar valores numéricos en PIEZAS
            if "PIEZAS" in df.columns:
                piezas_numeric = pd.to_numeric(df["PIEZAS"], errors='coerce')
                invalid_piezas = piezas_numeric.isna().sum()
                if invalid_piezas > 0:
                    validation["warnings"].append(
                        f"{invalid_piezas} valores no numéricos en columna PIEZAS"
                    )
            
            # Determinar si es válido
            validation["is_valid"] = len(validation["errors"]) == 0
            
            logger.info(f"Validación Urbano: {'VÁLIDO' if validation['is_valid'] else 'INVÁLIDO'}")
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validando datos Urbano: {e}")
            return {
                "is_valid": False,
                "errors": [f"Error en validación: {str(e)}"],
                "warnings": [],
                "missing_columns": [],
                "empty_required_fields": []
            }


# Funciones de utilidad para integración

def detect_and_load_urbano(file_path: Path) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Detecta y carga archivo Urbano si corresponde.
    
    Args:
        file_path: Ruta del archivo
        
    Returns:
        Tupla con DataFrame (None si no es Urbano) y metadatos
    """
    try:
        if UrbanoCodeDetector.is_urbano_file(file_path):
            df, metadata = UrbanoCodeDetector.load_urbano_file(file_path)
            return df, metadata
        else:
            return None, {"file_type": "not_urbano"}
            
    except Exception as e:
        logger.error(f"Error en detección/carga Urbano: {e}")
        return None, {"file_type": "error", "error": str(e)}


def get_urbano_processing_config(urbano_code: str) -> Dict[str, Any]:
    """
    Obtiene configuración específica para procesamiento Urbano.
    
    Args:
        urbano_code: Código Urbano de 9 dígitos
        
    Returns:
        Configuración de procesamiento
    """
    return {
        "mode": "urbano",
        "urbano_code": urbano_code,
        "required_columns": ["GUIA", "CLIENTE", "LOCALIDAD", "PIEZAS"],
        "numeric_columns": ["PIEZAS", "PESO", "DIAS", "COD RASTREO"],
        "sum_columns": ["PIEZAS", "PESO"],
        "group_by_columns": ["CLIENTE", "LOCALIDAD"],
        "header_row": 1,
        "skip_empty_rows": True,
        "auto_detect_structure": True
    }

