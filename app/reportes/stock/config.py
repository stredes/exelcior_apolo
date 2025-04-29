# app/reports/stock/config.py

from dataclasses import dataclass
from typing import List
from pathlib import Path
import json

@dataclass
class StockReportConfig:
    """
    Configuración para el generador de Informes de Stock Físico.
    Lee la sección "stock" de stock_report_config.json.
    """
    eliminar: List[str]
    sumar: List[str]
    mantener_formato: List[str]
    date_field: str
    start_row: int
    export_dir: Path

    @classmethod
    def load(cls, json_path: Path) -> "StockReportConfig":
        """
        Carga el JSON en json_path y devuelve la configuración de 'stock'.
        """
        if not json_path.exists():
            raise FileNotFoundError(f"No se encontró {json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        section = data.get("stock")
        if section is None:
            raise KeyError(f"No hay sección 'stock' en {json_path}")

        return cls(
            eliminar         = section.get("eliminar", []),
            sumar            = section.get("sumar", []),
            mantener_formato = section.get("mantener_formato", []),
            date_field       = section.get("date_field", "Fecha"),
            start_row        = section.get("start_row", 0),
            export_dir       = Path(section.get("export_dir", "exportados/stock"))
        )
