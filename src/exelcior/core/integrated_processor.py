"""
Procesador integrado de Excel para Exelcior Apolo
Combina todas las funcionalidades de procesamiento en una sola clase
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from .urbano_system import UrbanoDetectionSystem, UrbanoProcessor


class IntegratedExcelProcessor:
    """Procesador integrado para archivos Excel con todas las funcionalidades"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_default_config()
        
        # Inicializar sistema urbano perfecto
        self.urbano_detection = UrbanoDetectionSystem()
        self.urbano_processor = UrbanoProcessor()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Cargar configuración por defecto para todos los modos"""
        return {
            "fedex": {
                "eliminar": [
                    "errors", "senderAccountNumber", "poNumber", "senderLine1",
                    "senderPostcode", "totalShipmentWeight", "weightUnits",
                    "recipientPostcode", "creationDate", "recipientPhoneExtension",
                    "senderContactNumber", "senderCity", "length", "senderEmail",
                    "senderLine2", "recipientState", "packageWeight", "returnRmaNumber",
                    "invoiceNumber", "paymentType", "senderContactName",
                    "recipientContactNumber", "departmentNumber", "senderState",
                    "status", "recipientTin", "estimatedShippingCosts",
                    "recipientEmail", "senderCompany", "recipientResidential",
                    "senderPhoneExtension", "senderTin", "height", "returnReason",
                    "width", "etdEnabled", "quoteId", "recipientLine2",
                    "recipientCountry", "senderResidential", "recipientLine1",
                    "pickupId", "returnTrackingId", "senderLine3", "shipmentType",
                    "senderCountry"
                ],
                "sumar": ["numberOfPackages"],
                "mantener_formato": ["masterTrackingNumber"],
                "start_row": 0,
                "nombre_archivo_digitos": [],
                "vista_previa_fuente": 10,
            },
            "urbano": {
                "eliminar": [
                    "AGENCIA", "SHIPPER", "FECHA CHK", "DIAS", "ESTADO", 
                    "SERVICIO", "PESO"
                ],
                "sumar": ["PIEZAS"],
                "mantener_formato": [],
                "start_row": 2,
                "nombre_archivo_digitos": [9, 10],
                "vista_previa_fuente": 10,
            },
            "listados": {
                "eliminar": [
                    "Moneda", "Fecha doc.", "RUT", "Vendedor", "Glosa", 
                    "Total", "Tipo cambio"
                ],
                "sumar": [],
                "mantener_formato": [],
                "start_row": 0,
                "nombre_archivo_digitos": [],
                "vista_previa_fuente": 10,
            },
        }
    
    def validate_file(self, file_path: str) -> bool:
        """Validar archivo Excel"""
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.error(f"Archivo no encontrado: {file_path}")
                return False
            
            if path.suffix.lower() not in ['.xlsx', '.xls', '.csv', '.xlsm', '.xlsb']:
                self.logger.error(f"Formato no soportado: {path.suffix}")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validando archivo: {e}")
            return False
    
    def detect_file_mode(self, file_path: str) -> str:
        """Detectar automáticamente el modo del archivo con sistema urbano perfecto"""
        filename = Path(file_path).stem.lower()
        
        # Detección urbano con sistema perfecto
        if self.urbano_detection.is_urbano_filename(filename):
            self.logger.info(f"🏢 Archivo urbano detectado automáticamente: {filename}")
            return "urbano"
        
        # Detección FedEx
        if "fedex" in filename or "shipment" in filename:
            self.logger.info(f"📦 Archivo FedEx detectado: {filename}")
            return "fedex"
        
        # Detección listados
        if "lista" in filename or "venta" in filename or "listado" in filename:
            self.logger.info(f"📋 Archivo de listados detectado: {filename}")
            return "listados"
        
        # Por defecto: listados
        self.logger.info(f"📋 Modo por defecto asignado: listados")
        return "listados"
    
    def load_excel(self, file_path: str, mode: str = None) -> pd.DataFrame:
        """Cargar archivo Excel con configuración específica del modo"""
        if not self.validate_file(file_path):
            raise ValueError(f"Archivo no válido: {file_path}")
        
        if mode is None:
            mode = self.detect_file_mode(file_path)
        
        config = self.config.get(mode, self.config["listados"])
        start_row = config.get("start_row", 0)
        
        try:
            path_obj = Path(file_path)
            ext = path_obj.suffix.lower()
            
            # Seleccionar engine apropiado
            if ext in ['.xlsx', '.xlsm']:
                engine = 'openpyxl'
            elif ext == '.xls':
                engine = 'xlrd'
            elif ext == '.xlsb':
                engine = 'pyxlsb'
            else:
                engine = None
            
            # Cargar archivo
            if engine:
                df = pd.read_excel(
                    path_obj, 
                    engine=engine, 
                    skiprows=start_row if start_row > 0 else None
                )
            else:
                df = pd.read_csv(path_obj, skiprows=start_row if start_row > 0 else None)
            
            if df.empty:
                raise ValueError("El archivo está vacío")
            
            # Normalizar nombres de columnas
            df.columns = [str(col).strip().upper().replace(" ", "_") for col in df.columns]
            
            self.logger.info(f"Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
            return df
            
        except Exception as e:
            self.logger.error(f"Error cargando archivo: {e}")
            raise
    
    def process_fedex_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Procesar datos específicos de FedEx"""
        required_cols = [
            "SHIPDATE", "MASTERTRACKINGNUMBER", "REFERENCE", 
            "RECIPIENTCITY", "RECIPIENTCONTACTNAME", "PIECETRACKINGNUMBER"
        ]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise KeyError(f"Columnas faltantes para FedEx: {missing_cols}")
        
        # Filtrar filas válidas
        df_clean = df[df["MASTERTRACKINGNUMBER"].notna()].copy()
        
        # Agrupar por tracking number
        grouped = df_clean.groupby("MASTERTRACKINGNUMBER").agg({
            "SHIPDATE": "first",
            "REFERENCE": "first", 
            "RECIPIENTCITY": "first",
            "RECIPIENTCONTACTNAME": "first",
            "PIECETRACKINGNUMBER": "count"
        }).reset_index()
        
        # Renombrar columnas
        grouped.columns = [
            "Tracking Number", "Fecha", "Referencia", 
            "Ciudad", "Receptor", "BULTOS"
        ]
        
        total_bultos = int(grouped["BULTOS"].sum())
        
        self.logger.info(f"FedEx procesado: {len(grouped)} envíos, {total_bultos} bultos")
        return grouped, total_bultos
    
    def process_urbano_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Procesar datos específicos de Urbano con sistema perfecto"""
        # Usar el procesador urbano especializado
        config = self.config["urbano"]
        
        # Validar estructura urbana
        is_valid, missing_cols = self.urbano_detection.validate_urbano_structure(df)
        if not is_valid:
            raise KeyError(f"Estructura urbana inválida. Columnas faltantes: {missing_cols}")
        
        # Procesar con el sistema urbano
        df_clean = df[df["CLIENTE"].notna()].copy()
        
        # Eliminar columnas configuradas
        cols_to_remove = config.get("eliminar", [])
        df_clean = df_clean.drop(columns=cols_to_remove, errors="ignore")
        
        # Procesar PIEZAS
        df_clean["PIEZAS"] = pd.to_numeric(df_clean["PIEZAS"], errors="coerce").fillna(0)
        df_clean["PIEZAS"] = df_clean["PIEZAS"].astype(int)
        
        # Limpiar datos de texto
        text_columns = ["CLIENTE", "CIUDAD"]
        for col in text_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip().str.upper()
        
        # Procesar fechas
        if "FECHA" in df_clean.columns:
            df_clean["FECHA"] = pd.to_datetime(df_clean["FECHA"], errors="coerce")

        # Incluir COD RASTREO como campo de referencia si está presente
        if "COD_RASTREO" in df_clean.columns:
            df_clean["COD_RASTREO"] = df_clean["COD_RASTREO"].astype(str).str.strip().str.upper()
            self.logger.info("🔗 Campo COD RASTREO incluido como referencia (normalizado)")
        
        # Ordenar datos
        if "FECHA" in df_clean.columns and "CLIENTE" in df_clean.columns:
            df_clean = df_clean.sort_values(["FECHA", "CLIENTE"])
        
        total_piezas = int(df_clean["PIEZAS"].sum())
        
        self.logger.info(f"🏢 Urbano procesado con sistema perfecto: {len(df_clean)} registros, {total_piezas} piezas")
        return df_clean, total_piezas

    
    def process_listados_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Procesar datos de listados"""
        config = self.config["listados"]
        
        # Eliminar columnas configuradas
        cols_to_remove = config.get("eliminar", [])
        df_clean = df.drop(columns=cols_to_remove, errors="ignore")
        
        # Mantener formato de columnas específicas
        format_cols = config.get("mantener_formato", [])
        for col in format_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str)
        
        total_records = len(df_clean)
        
        self.logger.info(f"Listados procesado: {total_records} registros")
        return df_clean, total_records
    
    def apply_transformation(self, df: pd.DataFrame, mode: str) -> Tuple[pd.DataFrame, Optional[int]]:
        """Aplicar transformación según el modo"""
        self.logger.info(f"Aplicando transformación para modo: {mode}")
        
        if mode.lower() == "fedex":
            return self.process_fedex_data(df)
        elif mode.lower() == "urbano":
            return self.process_urbano_data(df)
        elif mode.lower() == "listados":
            return self.process_listados_data(df)
        else:
            raise ValueError(f"Modo no soportado: {mode}")
    
    def remove_duplicates(self, df: pd.DataFrame, reference_col: str = "Reference") -> pd.DataFrame:
        """Eliminar duplicados basado en columna de referencia"""
        if reference_col not in df.columns:
            self.logger.warning(f"Columna {reference_col} no encontrada para eliminar duplicados")
            return df
        
        initial_count = len(df)
        df_clean = df.drop_duplicates(subset=[reference_col], keep="first")
        removed_count = initial_count - len(df_clean)
        
        if removed_count > 0:
            self.logger.info(f"Duplicados eliminados: {removed_count}")
        
        return df_clean
    
    def export_to_excel(self, df: pd.DataFrame, output_path: str, mode: str) -> str:
        """Exportar DataFrame a Excel con formato"""
        try:
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{mode}_procesado_{timestamp}.xlsx"
            full_path = output_dir / filename
            
            # Exportar con formato básico
            with pd.ExcelWriter(full_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=mode.capitalize(), index=False)
                
                # Obtener worksheet para formato
                worksheet = writer.sheets[mode.capitalize()]
                
                # Ajustar ancho de columnas
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            self.logger.info(f"Archivo exportado: {full_path}")
            return str(full_path)
            
        except Exception as e:
            self.logger.error(f"Error exportando a Excel: {e}")
            raise
    
    def get_processing_summary(self, df: pd.DataFrame, mode: str, total_value: Optional[int] = None) -> Dict[str, Any]:
        """Obtener resumen del procesamiento"""
        summary = {
            "mode": mode,
            "total_records": len(df),
            "columns": list(df.columns),
            "processing_time": datetime.now().isoformat(),
        }
        
        if total_value is not None:
            if mode == "fedex":
                summary["total_bultos"] = total_value
            elif mode == "urbano":
                summary["total_piezas"] = total_value
            else:
                summary["total_items"] = total_value
        
        return summary
    
    def process_file_complete(self, file_path: str, mode: str = None) -> Dict[str, Any]:
        """Procesamiento completo de archivo con sistema urbano perfecto"""
        try:
            # Detectar modo si no se especifica
            if mode is None:
                mode = self.detect_file_mode(file_path)
            
            # Para archivos urbanos, usar procesamiento especializado
            if mode.lower() == "urbano":
                return self._process_urbano_complete(file_path)
            
            # Cargar archivo para otros modos
            df = self.load_excel(file_path, mode)
            
            # Aplicar transformaciones
            df_transformed, total_value = self.apply_transformation(df, mode)
            
            # Eliminar duplicados si es FedEx
            if mode.lower() == "fedex":
                df_transformed = self.remove_duplicates(df_transformed)
            
            # Generar resumen
            summary = self.get_processing_summary(df_transformed, mode, total_value)
            
            return {
                "success": True,
                "data": df_transformed,
                "summary": summary,
                "mode": mode
            }
            
        except Exception as e:
            self.logger.error(f"Error en procesamiento completo: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": mode
            }
    
    def _process_urbano_complete(self, file_path: str) -> Dict[str, Any]:
        """Procesamiento completo especializado para archivos urbanos"""
        try:
            # Usar el procesador urbano especializado
            result = self.urbano_processor.process_urbano_file(file_path, self.config["urbano"])
            
            if result["success"]:
                # Adaptar formato de respuesta
                summary = {
                    "mode": "urbano",
                    "total_records": result["stats"]["total_registros"],
                    "total_piezas": result["stats"]["total_piezas"],
                    "clientes_unicos": result["stats"]["clientes_unicos"],
                    "ciudades_unicas": result["stats"]["ciudades_unicas"],
                    "processing_time": datetime.now().isoformat(),
                    "detection_info": result["detection"]
                }
                
                return {
                    "success": True,
                    "data": result["data"],
                    "summary": summary,
                    "mode": "urbano",
                    "urbano_stats": result["stats"],
                    "detection": result["detection"]
                }
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"Error en procesamiento urbano completo: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "urbano"
            }

