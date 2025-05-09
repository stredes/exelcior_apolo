from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from app.core.logger_bod1 import capturar_log_bod1
from app.reportes.stock.config import StockReportConfig


class StockReportService:
    """
    Carga y prepara el DataFrame de 'Stock físico':
      - Lee .xls/.xlsx/.csv
      - Elimina columnas
      - Conserva formato
      - Calcula 'Días a vencimiento'
      - Salta filtro inventario si no hay date_field
    """

    def __init__(self, cfg: StockReportConfig):
        self.cfg = cfg

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        skip = self.cfg.start_row
        ext = file_path.suffix.lower()
        if ext == ".xls":
            return pd.read_excel(
                file_path, sheet_name="Stock físico", skiprows=skip, engine="xlrd"
            )
        if ext == ".xlsx":
            return pd.read_excel(
                file_path, sheet_name="Stock físico", skiprows=skip, engine="openpyxl"
            )
        if ext == ".csv":
            return pd.read_csv(file_path, skiprows=skip)
        raise ValueError(f"Formato no soportado: {ext}")

    def generate(
        self,
        file_path: Path,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> pd.DataFrame:
        capturar_log_bod1(f"Cargando stock: {file_path}", nivel="info")
        df = self._read_file(file_path)

        # DEBUG: columnas leídas
        capturar_log_bod1(f"Columnas: {list(df.columns)}", nivel="info")

        # 1) Eliminar columnas
        df = df.drop(columns=self.cfg.eliminar, errors="ignore")

        # 2) Mantener formato en texto
        for col in self.cfg.mantener_formato:
            if col in df.columns:
                df[col] = df[col].astype(str)

        # 3) Filtro inventario condicional
        if (
            self.cfg.date_field
            and self.cfg.date_field in df.columns
            and fecha_desde
            and fecha_hasta
        ):
            df[self.cfg.date_field] = pd.to_datetime(
                df[self.cfg.date_field], dayfirst=True, errors="coerce"
            )
            mask = (df[self.cfg.date_field] >= fecha_desde) & (
                df[self.cfg.date_field] <= fecha_hasta
            )
            df = df.loc[mask]
        else:
            capturar_log_bod1(
                f"Salto filtro inventario: '{self.cfg.date_field}'", nivel="warning"
            )

        df = df.reset_index(drop=True)

        # 4) Días a vencimiento
        if "Fecha Vencimiento" in df.columns:
            df["Fecha Vencimiento"] = pd.to_datetime(
                df["Fecha Vencimiento"], format="%d/%m/%Y", errors="coerce"
            )
            hoy = pd.to_datetime(datetime.today().date())
            df["Días a vencimiento"] = (df["Fecha Vencimiento"] - hoy).dt.days
        else:
            df["Días a vencimiento"] = None

        capturar_log_bod1(f"Total registros: {len(df)}", nivel="info")
        return df

    def export(self, df: pd.DataFrame, file_name: Optional[str] = None) -> Path:
        self.cfg.export_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = file_name or f"stock_{ts}.xlsx"
        out = self.cfg.export_dir / fname
        df.to_excel(out, index=False)
        capturar_log_bod1(f"Informe exportado: {out}", nivel="info")
        return out
