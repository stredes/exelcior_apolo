"""
Sistema de carga automática refactorizado para Exelcior Apolo.

Maneja la detección y carga automática de archivos según patrones
y configuraciones específicas por modo de operación.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from ..constants import OPERATION_MODES, DEFAULT_PATHS
from ..config import config_manager
from ..utils import get_logger, FileValidator, ValidationError

logger = get_logger("exelcior.core.autoloader")


class FilePattern:
    """Representa un patrón de archivo para detección automática."""
    
    def __init__(self, name: str, pattern: str, mode: str, priority: int = 0):
        """
        Inicializa un patrón de archivo.
        
        Args:
            name: Nombre descriptivo del patrón
            pattern: Expresión regular para el patrón
            mode: Modo de operación asociado
            priority: Prioridad del patrón (mayor número = mayor prioridad)
        """
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.mode = mode
        self.priority = priority

    def matches(self, filename: str) -> bool:
        """Verifica si un archivo coincide con el patrón."""
        return bool(self.pattern.search(filename))


class AutoLoader:
    """
    Cargador automático de archivos.
    
    Detecta automáticamente archivos relevantes en directorios configurados
    y los asocia con modos de operación apropiados.
    """

    def __init__(self):
        """Inicializa el autoloader con patrones predefinidos."""
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> List[FilePattern]:
        """Inicializa los patrones de detección de archivos."""
        return [
            # Patrones para FedEx
            FilePattern(
                "FedEx Tracking",
                r"fedex|tracking|shipment|envio.*fedex",
                "fedex",
                priority=10
            ),
            FilePattern(
                "FedEx Numbers",
                r"\d{12,15}",  # Números de tracking típicos
                "fedex",
                priority=5
            ),
            
            # Patrones para Urbano
            FilePattern(
                "Urbano Delivery",
                r"urbano|delivery|entrega|reparto",
                "urbano",
                priority=10
            ),
            FilePattern(
                "Urbano ID File",
                r"^\d{9}\.xlsx$",
                "urbano",
                priority=15  # Alta prioridad, porque es un patrón exclusivo
            ),

            
            # Patrones para Listados
            FilePattern(
                "General List",
                r"listado|lista|reporte|report",
                "listados",
                priority=8
            ),
            FilePattern(
                "Inventory",
                r"inventario|stock|productos",
                "listados",
                priority=6
            ),
            
            # Patrones por fecha (más específicos)
            FilePattern(
                "Daily Report",
                r"\d{4}[-_]\d{2}[-_]\d{2}",  # YYYY-MM-DD
                "listados",
                priority=3
            ),
            FilePattern(
                "Date Pattern",
                r"\d{2}[-_]\d{2}[-_]\d{4}",  # DD-MM-YYYY
                "listados",
                priority=2
            )
        ]

    def find_latest_file(
        self, 
        mode: Optional[str] = None,
        directory: Optional[Path] = None
    ) -> Tuple[Optional[Path], str]:
        """
        Encuentra el archivo más reciente para un modo específico.
        
        Args:
            mode: Modo de operación específico. Si es None, busca en todos.
            directory: Directorio donde buscar. Si es None, usa configurado.
            
        Returns:
            Tupla con (archivo_encontrado, estado)
            Estados: "ok", "no_match", "empty_folder", "error"
        """
        try:
            search_dir = directory or self._get_search_directory(mode)
            
            if not search_dir.exists():
                logger.warning(f"Directorio no existe: {search_dir}")
                return None, "empty_folder"
            
            # Obtener archivos candidatos
            candidates = self._get_file_candidates(search_dir)
            
            if not candidates:
                logger.info(f"No se encontraron archivos en: {search_dir}")
                return None, "empty_folder"
            
            # Filtrar por modo si se especifica
            if mode:
                filtered_candidates = self._filter_by_mode(candidates, mode)
                if not filtered_candidates:
                    logger.info(f"No se encontraron archivos para modo {mode}")
                    return None, "no_match"
                candidates = filtered_candidates
            
            # Seleccionar el más reciente
            latest_file = self._select_latest_file(candidates)
            
            if latest_file:
                logger.info(f"Archivo más reciente encontrado: {latest_file}")
                return latest_file, "ok"
            else:
                return None, "no_match"
                
        except Exception as e:
            logger.error(f"Error en búsqueda automática: {e}")
            return None, "error"

    def _get_search_directory(self, mode: Optional[str]) -> Path:
        """Obtiene el directorio de búsqueda para un modo."""
        if mode:
            custom_path = config_manager.get_download_path(mode)
            if custom_path.exists():
                return custom_path
        
        # Usar directorio por defecto
        return DEFAULT_PATHS["downloads"]

    def _get_file_candidates(self, directory: Path) -> List[Path]:
        """Obtiene lista de archivos candidatos en un directorio."""
        candidates = []
        
        try:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    try:
                        # Validar que es un archivo soportado
                        FileValidator.validate_file_format(file_path)
                        FileValidator.validate_file_size(file_path)
                        candidates.append(file_path)
                    except ValidationError:
                        # Archivo no válido, continuar
                        continue
        except PermissionError:
            logger.warning(f"Sin permisos para leer directorio: {directory}")
        
        return candidates

    def _filter_by_mode(self, candidates: List[Path], mode: str) -> List[Path]:
        """Filtra archivos candidatos por modo de operación."""
        filtered = []
        
        for file_path in candidates:
            detected_mode = self.detect_file_mode(file_path)
            if detected_mode == mode:
                filtered.append(file_path)
        
        return filtered

    def _select_latest_file(self, candidates: List[Path]) -> Optional[Path]:
        """Selecciona el archivo más reciente de una lista de candidatos."""
        if not candidates:
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        candidates_with_time = [
            (file_path, file_path.stat().st_mtime)
            for file_path in candidates
        ]
        
        candidates_with_time.sort(key=lambda x: x[1], reverse=True)
        return candidates_with_time[0][0]

    def detect_file_mode(self, file_path: Path) -> Optional[str]:
        """
        Detecta el modo de operación más probable para un archivo.
        
        Args:
            file_path: Ruta del archivo a analizar
            
        Returns:
            Modo detectado o None si no se puede determinar
        """
        filename = file_path.name

        # Añadir caso especial: archivo de 9 dígitos terminado en .xlsx
        if re.match(r"^\d{9}\.xlsx$", filename):
            logger.info(f"Archivo {filename} detectado como modo urbano (formato numérico de 9 dígitos)")
            return "urbano"
        
        # Buscar patrones que coincidan
        matching_patterns = []
        for pattern in self.patterns:
            if pattern.matches(filename):
                matching_patterns.append(pattern)
        
        if not matching_patterns:
            logger.warning(f"No se pudo detectar modo para archivo: {filename}")
            return None
        
        # Seleccionar patrón con mayor prioridad
        best_pattern = max(matching_patterns, key=lambda p: p.priority)

        logger.info(f"Archivo {filename} detectado como modo {best_pattern.mode} "
                    f"(patrón: {best_pattern.name})")
        
        return best_pattern.mode


    def get_recent_files(self, mode: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene lista de archivos recientes procesados.
        
        Args:
            mode: Filtrar por modo específico
            limit: Número máximo de archivos a retornar
            
        Returns:
            Lista de diccionarios con información de archivos
        """
        recent_files = config_manager.get_recent_files()
        
        if mode:
            recent_files = [f for f in recent_files if f.get("mode") == mode]
        
        # Limitar resultados
        recent_files = recent_files[:limit]
        
        # Enriquecer con información actual del archivo
        enriched_files = []
        for file_info in recent_files:
            file_path = Path(file_info["path"])
            if file_path.exists():
                try:
                    stat = file_path.stat()
                    enriched_info = {
                        **file_info,
                        "exists": True,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                    enriched_files.append(enriched_info)
                except Exception:
                    # Archivo no accesible
                    enriched_files.append({**file_info, "exists": False})
            else:
                enriched_files.append({**file_info, "exists": False})
        
        return enriched_files

    def set_custom_directory(self, mode: str, directory: Path) -> None:
        """
        Establece un directorio personalizado para un modo.
        
        Args:
            mode: Modo de operación
            directory: Directorio personalizado
        """
        if not directory.exists():
            raise ValidationError(f"Directorio no existe: {directory}")
        
        if not directory.is_dir():
            raise ValidationError(f"La ruta no es un directorio: {directory}")
        
        config_manager.set_download_path(mode, directory)
        logger.info(f"Directorio personalizado establecido para {mode}: {directory}")

    def add_custom_pattern(self, name: str, pattern: str, mode: str, priority: int = 5) -> None:
        """
        Añade un patrón personalizado de detección.
        
        Args:
            name: Nombre del patrón
            pattern: Expresión regular
            mode: Modo asociado
            priority: Prioridad del patrón
        """
        try:
            custom_pattern = FilePattern(name, pattern, mode, priority)
            self.patterns.append(custom_pattern)
            logger.info(f"Patrón personalizado añadido: {name} -> {mode}")
        except re.error as e:
            raise ValidationError(f"Patrón regex inválido: {e}")

    def get_directory_stats(self, directory: Optional[Path] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un directorio.
        
        Args:
            directory: Directorio a analizar
            
        Returns:
            Diccionario con estadísticas
        """
        search_dir = directory or DEFAULT_PATHS["downloads"]
        
        if not search_dir.exists():
            return {"error": "Directorio no existe"}
        
        try:
            all_files = list(search_dir.iterdir())
            excel_files = [f for f in all_files if f.is_file() and 
                          f.suffix.lower() in ['.xlsx', '.xls', '.csv']]
            
            mode_counts = {}
            for file_path in excel_files:
                mode = self.detect_file_mode(file_path)
                mode_counts[mode or "unknown"] = mode_counts.get(mode or "unknown", 0) + 1
            
            return {
                "directory": str(search_dir),
                "total_files": len(all_files),
                "excel_files": len(excel_files),
                "mode_distribution": mode_counts,
                "last_scan": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {"error": str(e)}


# Instancia global del autoloader
autoloader = AutoLoader()

