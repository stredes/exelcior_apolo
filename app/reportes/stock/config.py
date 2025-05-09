import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class StockReportConfig:
    eliminar: List[str]
    sumar: List[str]
    mantener_formato: List[str]
    date_field: Optional[str]  # campo de fecha de inventario, o None
    start_row: int  # filas a saltar al leer
    export_dir: Path  # carpeta de salida
    thresholds: Dict[str, int]  # umbrales de criticidad
    vencimiento_alert_days: int  # días para alerta de vencimiento

    @classmethod
    def load(cls, json_path: Path) -> "StockReportConfig":
        data = json.loads(json_path.read_text(encoding="utf-8"))
        sec = data.get("stock", {})
        return cls(
            eliminar=sec.get("eliminar", []),
            sumar=sec.get("sumar", []),
            mantener_formato=sec.get("mantener_formato", []),
            date_field=sec.get("date_field") or None,
            start_row=sec.get("start_row", 0),
            export_dir=Path(sec.get("export_dir", "exportados/stock")),
            thresholds=sec.get("thresholds", {"critico": 5, "bajo": 20, "alto": 50}),
            vencimiento_alert_days=sec.get("vencimiento_alert_days", 90),
        )
