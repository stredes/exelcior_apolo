"""
Sistema Urbano Perfecto para Exelcior Apolo
Detección automática y procesamiento especializado para archivos urbanos
"""

import re
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
from datetime import datetime


class UrbanoDetectionSystem:
    """Sistema de detección automática para archivos urbanos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.digit_patterns = [9, 10]  # Patrones de dígitos válidos
        self.required_columns = ["FECHA", "CLIENTE", "CIUDAD", "PIEZAS"]
        
    def is_urbano_filename(self, filename: str, digit_lengths: List[int] = None) -> bool:
        """Detectar si un archivo es urbano por su nombre"""
        if digit_lengths is None:
            digit_lengths = self.digit_patterns
            
        stem = Path(filename).stem
        
        # Verificar si es solo dígitos
        if not stem.isdigit():
            return False
            
        # Verificar longitud
        return len(stem) in digit_lengths
    
    def validate_urbano_structure(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validar estructura de archivo urbano"""
        missing_columns = []
        
        # Normalizar nombres de columnas
        df_columns = [str(col).strip().upper().replace(" ", "_") for col in df.columns]
        
        for required_col in self.required_columns:
            if required_col not in df_columns:
                missing_columns.append(required_col)
        
        is_valid = len(missing_columns) == 0
        
        if is_valid:
            self.logger.info("✅ Estructura urbana válida detectada")
        else:
            self.logger.warning(f"❌ Columnas faltantes: {missing_columns}")
            
        return is_valid, missing_columns
    
    def detect_urbano_auto(self, file_path: str, df: pd.DataFrame = None) -> Dict[str, Any]:
        """Detección automática completa de archivo urbano"""
        filename = Path(file_path).name
        
        # Paso 1: Verificar nombre de archivo
        filename_match = self.is_urbano_filename(filename)
        
        # Paso 2: Verificar estructura si se proporciona DataFrame
        structure_valid = False
        missing_cols = []
        
        if df is not None:
            structure_valid, missing_cols = self.validate_urbano_structure(df)
        
        # Determinar resultado
        is_urbano = filename_match and (df is None or structure_valid)
        confidence = 0.0
        
        if filename_match:
            confidence += 0.6
        if structure_valid:
            confidence += 0.4
        
        result = {
            "is_urbano": is_urbano,
            "confidence": confidence,
            "filename_match": filename_match,
            "structure_valid": structure_valid,
            "missing_columns": missing_cols,
            "detected_pattern": len(Path(file_path).stem) if filename_match else None
        }
        
        self.logger.info(f"Detección urbana: {result}")
        return result


class UrbanoProcessor:
    """Procesador especializado para archivos urbanos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detection_system = UrbanoDetectionSystem()
        
    def process_urbano_file(self, file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Procesamiento completo de archivo urbano"""
        try:
            self.logger.info(f"🏢 Iniciando procesamiento urbano: {file_path}")
            
            # Configuración por defecto
            if config is None:
                config = {
                    "start_row": 2,
                    "eliminar": ["AGENCIA", "SHIPPER", "FECHA CHK", "DIAS", "ESTADO", "SERVICIO", "PESO"],
                    "sumar": ["PIEZAS"],
                    "mantener_formato": []
                }
            
            # Cargar archivo
            df = self._load_urbano_file(file_path, config.get("start_row", 2))
            
            # Detección automática
            detection_result = self.detection_system.detect_urbano_auto(file_path, df)
            
            if not detection_result["is_urbano"]:
                raise ValueError(f"Archivo no es urbano válido: {detection_result}")
            
            # Validar columnas requeridas
            self._validate_required_columns(df)
            
            # Procesar datos
            df_processed = self._process_urbano_data(df, config)
            
            # Calcular estadísticas
            stats = self._calculate_urbano_stats(df_processed)
            
            result = {
                "success": True,
                "data": df_processed,
                "stats": stats,
                "detection": detection_result,
                "mode": "urbano",
                "file_info": {
                    "filename": Path(file_path).name,
                    "size": Path(file_path).stat().st_size,
                    "modified": datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                }
            }
            
            self.logger.info(f"✅ Procesamiento urbano completado: {stats['total_piezas']} piezas")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error en procesamiento urbano: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "urbano"
            }
    
    def _load_urbano_file(self, file_path: str, start_row: int = 2) -> pd.DataFrame:
        """Cargar archivo urbano con configuración específica"""
        try:
            path_obj = Path(file_path)
            ext = path_obj.suffix.lower()
            
            # Seleccionar engine
            if ext in ['.xlsx', '.xlsm']:
                engine = 'openpyxl'
            elif ext == '.xls':
                engine = 'xlrd'
            else:
                engine = None
            
            # Cargar con skiprows
            skiprows = list(range(start_row)) if start_row > 0 else None
            
            if engine:
                df = pd.read_excel(path_obj, engine=engine, skiprows=skiprows)
            else:
                df = pd.read_csv(path_obj, skiprows=skiprows)
            
            if df.empty:
                raise ValueError("Archivo urbano está vacío")
            
            # Normalizar columnas
            df.columns = [str(col).strip().upper().replace(" ", "_") for col in df.columns]
            
            self.logger.info(f"Archivo urbano cargado: {len(df)} filas, {len(df.columns)} columnas")
            return df
            
        except Exception as e:
            self.logger.error(f"Error cargando archivo urbano: {e}")
            raise
    
    def _validate_required_columns(self, df: pd.DataFrame):
        """Validar columnas requeridas para urbano"""
        required = self.detection_system.required_columns
        df_columns = list(df.columns)
        
        missing = [col for col in required if col not in df_columns]
        
        if missing:
            raise KeyError(f"Columnas requeridas faltantes para urbano: {missing}")
        
        self.logger.info("✅ Validación de columnas urbanas exitosa")
    
    def _process_urbano_data(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Procesar datos específicos de urbano"""
        df_processed = df.copy()
        
        # Filtrar filas válidas (con cliente)
        df_processed = df_processed[df_processed["CLIENTE"].notna()].copy()
        
        # Eliminar columnas configuradas
        cols_to_remove = config.get("eliminar", [])
        df_processed = df_processed.drop(columns=cols_to_remove, errors="ignore")
        
        # Procesar columnas numéricas (PIEZAS)
        if "PIEZAS" in df_processed.columns:
            df_processed["PIEZAS"] = pd.to_numeric(df_processed["PIEZAS"], errors="coerce").fillna(0)
            df_processed["PIEZAS"] = df_processed["PIEZAS"].astype(int)
        
        # Limpiar y normalizar datos de texto
        text_columns = ["CLIENTE", "CIUDAD"]
        for col in text_columns:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].astype(str).str.strip().str.upper()
        
        # Procesar fechas
        if "FECHA" in df_processed.columns:
            df_processed["FECHA"] = pd.to_datetime(df_processed["FECHA"], errors="coerce")
        
        # Mantener formato de columnas específicas
        format_cols = config.get("mantener_formato", [])
        for col in format_cols:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].astype(str)
        
        # Ordenar por fecha y cliente
        if "FECHA" in df_processed.columns and "CLIENTE" in df_processed.columns:
            df_processed = df_processed.sort_values(["FECHA", "CLIENTE"])
        
        self.logger.info(f"Datos urbanos procesados: {len(df_processed)} registros válidos")
        return df_processed
    
    def _calculate_urbano_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcular estadísticas específicas de urbano"""
        stats = {
            "total_registros": len(df),
            "total_piezas": int(df["PIEZAS"].sum()) if "PIEZAS" in df.columns else 0,
            "clientes_unicos": df["CLIENTE"].nunique() if "CLIENTE" in df.columns else 0,
            "ciudades_unicas": df["CIUDAD"].nunique() if "CIUDAD" in df.columns else 0,
        }
        
        # Estadísticas por ciudad
        if "CIUDAD" in df.columns and "PIEZAS" in df.columns:
            stats["por_ciudad"] = df.groupby("CIUDAD")["PIEZAS"].sum().to_dict()
        
        # Estadísticas por cliente
        if "CLIENTE" in df.columns and "PIEZAS" in df.columns:
            top_clientes = df.groupby("CLIENTE")["PIEZAS"].sum().nlargest(5).to_dict()
            stats["top_clientes"] = top_clientes
        
        # Rango de fechas
        if "FECHA" in df.columns:
            fechas_validas = df["FECHA"].dropna()
            if not fechas_validas.empty:
                stats["fecha_inicio"] = fechas_validas.min().strftime("%Y-%m-%d")
                stats["fecha_fin"] = fechas_validas.max().strftime("%Y-%m-%d")
        
        return stats
    
    def generate_urbano_report(self, stats: Dict[str, Any], detection: Dict[str, Any]) -> str:
        """Generar reporte detallado del procesamiento urbano"""
        report = f"""
🏢 REPORTE DE PROCESAMIENTO URBANO

📊 RESUMEN GENERAL:
• Total de registros: {stats['total_registros']:,}
• Total de piezas: {stats['total_piezas']:,}
• Clientes únicos: {stats['clientes_unicos']:,}
• Ciudades únicas: {stats['ciudades_unicas']:,}

🔍 DETECCIÓN AUTOMÁTICA:
• Patrón de archivo: {'✅ Detectado' if detection['filename_match'] else '❌ No detectado'}
• Estructura válida: {'✅ Válida' if detection['structure_valid'] else '❌ Inválida'}
• Confianza: {detection['confidence']:.1%}
• Dígitos detectados: {detection.get('detected_pattern', 'N/A')}

📅 RANGO DE FECHAS:
• Desde: {stats.get('fecha_inicio', 'N/A')}
• Hasta: {stats.get('fecha_fin', 'N/A')}

🏙️ TOP CIUDADES:
"""
        
        # Agregar top ciudades
        if "por_ciudad" in stats:
            for ciudad, piezas in list(stats["por_ciudad"].items())[:5]:
                report += f"• {ciudad}: {piezas:,} piezas\n"
        
        report += "\n👥 TOP CLIENTES:\n"
        
        # Agregar top clientes
        if "top_clientes" in stats:
            for cliente, piezas in stats["top_clientes"].items():
                report += f"• {cliente}: {piezas:,} piezas\n"
        
        return report


class UrbanoAutoLoader:
    """Cargador automático para archivos urbanos"""
    
    def __init__(self, download_folder: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        self.download_folder = download_folder or Path.home() / "Descargas"
        self.detection_system = UrbanoDetectionSystem()
        
    def find_latest_urbano_file(self) -> Tuple[Optional[Path], str]:
        """Encontrar el archivo urbano más reciente"""
        try:
            if not self.download_folder.exists():
                return None, "folder_not_found"
            
            # Buscar archivos Excel
            excel_files = []
            for pattern in ["*.xlsx", "*.xls"]:
                excel_files.extend(self.download_folder.glob(pattern))
            
            if not excel_files:
                return None, "no_excel_files"
            
            # Filtrar archivos urbanos
            urbano_files = []
            for file_path in excel_files:
                if self.detection_system.is_urbano_filename(file_path.name):
                    urbano_files.append(file_path)
            
            if not urbano_files:
                return None, "no_urbano_files"
            
            # Ordenar por fecha de modificación (más reciente primero)
            urbano_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            latest_file = urbano_files[0]
            self.logger.info(f"✅ Archivo urbano más reciente: {latest_file.name}")
            
            return latest_file, "success"
            
        except Exception as e:
            self.logger.error(f"Error buscando archivos urbanos: {e}")
            return None, "error"
    
    def auto_load_and_process(self, processor: UrbanoProcessor) -> Dict[str, Any]:
        """Carga automática y procesamiento de archivo urbano"""
        try:
            # Buscar archivo más reciente
            file_path, status = self.find_latest_urbano_file()
            
            if status != "success" or file_path is None:
                return {
                    "success": False,
                    "error": f"No se encontró archivo urbano: {status}",
                    "status": status
                }
            
            # Procesar archivo
            result = processor.process_urbano_file(str(file_path))
            
            if result["success"]:
                result["auto_loaded"] = True
                result["file_path"] = str(file_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error en carga automática urbana: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "processing_error"
            }

