from pathlib import Path
import importlib.util

import pandas as pd
import pytest

from app.services.inventory_difference_service import (
    build_inventory_difference_report_df,
    close_inventory_difference_cycle,
    export_inventory_difference_report,
    export_inventory_difference_report_pdf,
    get_inventory_difference_summary,
    merge_inventory_differences,
)


CODIGO = "C\u00f3digo"
UBICACION = "Ubicaci\u00f3n"
SERIE = "N\u00b0 Serie"
OBSERVACION = "Observaci\u00f3n"
OBSERVACION_DIF = "Observaci\u00f3n Dif."


def _sample_diff_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 1,
                CODIGO: "A1",
                "Producto": "Reactivo",
                "Bodega": "Central",
                UBICACION: "01-A1",
                SERIE: "",
                "Lote": "LOT-01",
                "Fecha Vencimiento": "01/01/2027",
                "Stock Sistema": 10,
                "Dif. Stock": -3,
                "Stock Contado": 7,
                OBSERVACION: "Conteo f\u00edsico",
                "Archivo Origen": "inventario.xlsx",
                "Actualizado": "23/04/2026 12:00",
            }
        ]
    )


def test_merge_inventory_differences_adds_signed_difference():
    base = pd.DataFrame(
        [
            {
                CODIGO: "A1",
                "Producto": "Reactivo",
                "Bodega": "Central",
                UBICACION: "01-A1",
                SERIE: "",
                "Lote": "LOT-01",
                "Fecha Vencimiento": "01/01/2027",
                "Saldo Stock": 10,
            }
        ]
    )

    merged = merge_inventory_differences(base, _sample_diff_df())

    assert int(merged.loc[0, "Dif. Stock"]) == -3
    assert int(merged.loc[0, "Stock Contado"]) == 7
    assert merged.loc[0, OBSERVACION_DIF] == "Conteo f\u00edsico"


def test_merge_inventory_differences_defaults_when_no_match():
    base = pd.DataFrame(
        [
            {
                CODIGO: "A2",
                "Producto": "Control",
                "Bodega": "Central",
                UBICACION: "02-B4",
                SERIE: "SER-1",
                "Lote": "LOT-02",
                "Fecha Vencimiento": "01/01/2027",
                "Saldo Stock": 4,
            }
        ]
    )

    merged = merge_inventory_differences(base, pd.DataFrame())

    assert int(merged.loc[0, "Dif. Stock"]) == 0
    assert int(merged.loc[0, "Stock Contado"]) == 4
    assert merged.loc[0, OBSERVACION_DIF] == ""


def test_build_inventory_difference_report_df_keeps_expected_columns():
    report = build_inventory_difference_report_df(_sample_diff_df())

    assert "id" not in report.columns
    assert list(report.columns[:4]) == [CODIGO, "Producto", "Bodega", UBICACION]
    assert int(report.loc[0, "Dif. Stock"]) == -3


def test_get_inventory_difference_summary_counts_positive_and_negative():
    diff_df = pd.DataFrame(
        [
            {"Dif. Stock": 5},
            {"Dif. Stock": -2},
            {"Dif. Stock": -1},
        ]
    )

    summary = get_inventory_difference_summary(diff_df)

    assert summary["items"] == 3
    assert summary["positive_items"] == 1
    assert summary["negative_items"] == 2
    assert summary["net_difference"] == 2


def test_close_inventory_difference_cycle_archives_report_and_clears(monkeypatch, tmp_path):
    diff_df = _sample_diff_df()
    recorded: dict[str, object] = {}

    def fake_export(destination, diff_df=None):
        recorded["destination"] = Path(destination)
        recorded["rows"] = len(diff_df)
        Path(destination).write_text("ok", encoding="utf-8")
        return Path(destination)

    def fake_clear():
        recorded["cleared"] = True
        return 1

    monkeypatch.setattr("app.services.inventory_difference_service.export_inventory_difference_report", fake_export)
    monkeypatch.setattr("app.services.inventory_difference_service.clear_inventory_differences", fake_clear)
    monkeypatch.setattr("app.services.inventory_difference_service.OUTPUT_DIR", tmp_path)

    archive_path = close_inventory_difference_cycle(diff_df)

    assert archive_path.exists()
    assert archive_path.parent == tmp_path / "inventario_diferencias" / "historial_cierres"
    assert recorded["rows"] == 1
    assert recorded["cleared"] is True


def test_export_inventory_difference_report_creates_excel(tmp_path):
    output = tmp_path / "diferencias.xlsx"

    path = export_inventory_difference_report(output, diff_df=_sample_diff_df())

    assert path.exists()
    assert path.suffix == ".xlsx"


def test_export_inventory_difference_report_pdf_creates_pdf(tmp_path):
    output = tmp_path / "diferencias.pdf"
    if importlib.util.find_spec("reportlab") is None:
        with pytest.raises(RuntimeError):
            export_inventory_difference_report_pdf(output, diff_df=_sample_diff_df())
        return

    path = export_inventory_difference_report_pdf(output, diff_df=_sample_diff_df())

    assert path.exists()
    assert path.suffix == ".pdf"
