from pathlib import Path
import pandas as pd
from datetime import datetime

from app.reportes.stock.config import StockReportConfig
from app.core.logger_bod1 import capturar_log_bod1


class StockReportService:
    """
    Servicio para generar y exportar informes de stock físico.
    """

    def __init__(self, cfg: StockReportConfig):
        self.cfg = cfg

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """
        Lee el archivo (Excel .xls/.xlsx o CSV) saltándose las filas iniciales.
        """
        ext = file_path.suffix.lower()
        skiprows = self.cfg.start_row
        if ext in [".xlsx", ".xls"]:
            engine = "xlrd" if ext == ".xls" else "openpyxl"
            df = pd.read_excel(file_path, skiprows=skiprows, engine=engine)
        elif ext == ".csv":
            df = pd.read_csv(file_path, skiprows=skiprows)
        else:
            raise ValueError(f"Formato no soportado: {ext}")
        return df

    def generate(self, file_path: Path, fecha_desde: datetime, fecha_hasta: datetime) -> pd.DataFrame:
        """
        Genera el DataFrame de informe, filtrado por el rango de fechas.
        """
        capturar_log_bod1(f"[StockReport] Cargando archivo: {file_path}", nivel="info")

        # 1. Leer datos
        df = self._read_file(file_path)

        # 2. Eliminar columnas indeseadas
        df = df.drop(columns=self.cfg.eliminar, errors="ignore")

        # 3. Mantener formato en columnas específicas
        for col in self.cfg.mantener_formato:
            if col in df.columns:
                df[col] = df[col].astype(str)

        # 4. Convertir columna de fecha y filtrar por rango
        date_col = self.cfg.date_field
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        mask = (df[date_col] >= fecha_desde) & (df[date_col] <= fecha_hasta)
        df_filtrado = df.loc[mask].reset_index(drop=True)

        capturar_log_bod1(
            f"[StockReport] Filtrado: {len(df_filtrado)} filas entre {fecha_desde.date()} y {fecha_hasta.date()}",
            nivel="info"
        )

        return df_filtrado

    def export(self, df: pd.DataFrame, file_name: str = None) -> Path:
        """
        Exporta el DataFrame a un archivo Excel dentro de export_dir.
        """
        self.cfg.export_dir.mkdir(parents=True, exist_ok=True)
        if not file_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"stock_report_{ts}.xlsx"
        path = self.cfg.export_dir / file_name
        df.to_excel(path, index=False)
        capturar_log_bod1(f"[StockReport] Informe exportado a: {path}", nivel="info")
        return path
