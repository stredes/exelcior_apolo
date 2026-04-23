import pandas as pd

from app.services.inventory_difference_service import (
    build_inventory_difference_report_df,
    merge_inventory_differences,
)


def test_merge_inventory_differences_adds_signed_difference():
    base = pd.DataFrame(
        [
            {
                "Código": "A1",
                "Producto": "Reactivo",
                "Bodega": "Central",
                "Ubicación": "01-A1",
                "N° Serie": "",
                "Lote": "LOT-01",
                "Fecha Vencimiento": "01/01/2027",
                "Saldo Stock": 10,
            }
        ]
    )

    diff_df = pd.DataFrame(
        [
            {
                "id": 1,
                "Código": "A1",
                "Producto": "Reactivo",
                "Bodega": "Central",
                "Ubicación": "01-A1",
                "N° Serie": "",
                "Lote": "LOT-01",
                "Fecha Vencimiento": "01/01/2027",
                "Stock Sistema": 10,
                "Dif. Stock": -3,
                "Stock Contado": 7,
                "Observación": "Conteo físico",
                "Archivo Origen": "inventario.xlsx",
                "Actualizado": "23/04/2026 12:00",
            }
        ]
    )

    merged = merge_inventory_differences(base, diff_df)

    assert int(merged.loc[0, "Dif. Stock"]) == -3
    assert int(merged.loc[0, "Stock Contado"]) == 7
    assert merged.loc[0, "Observación Dif."] == "Conteo físico"


def test_merge_inventory_differences_defaults_when_no_match():
    base = pd.DataFrame(
        [
            {
                "Código": "A2",
                "Producto": "Control",
                "Bodega": "Central",
                "Ubicación": "02-B4",
                "N° Serie": "SER-1",
                "Lote": "LOT-02",
                "Fecha Vencimiento": "01/01/2027",
                "Saldo Stock": 4,
            }
        ]
    )

    merged = merge_inventory_differences(base, pd.DataFrame())

    assert int(merged.loc[0, "Dif. Stock"]) == 0
    assert int(merged.loc[0, "Stock Contado"]) == 4
    assert merged.loc[0, "Observación Dif."] == ""


def test_build_inventory_difference_report_df_keeps_expected_columns():
    diff_df = pd.DataFrame(
        [
            {
                "id": 1,
                "Código": "A1",
                "Producto": "Reactivo",
                "Bodega": "Central",
                "Ubicación": "01-A1",
                "N° Serie": "",
                "Lote": "LOT-01",
                "Fecha Vencimiento": "01/01/2027",
                "Stock Sistema": 10,
                "Dif. Stock": -3,
                "Stock Contado": 7,
                "Observación": "Conteo físico",
                "Archivo Origen": "inventario.xlsx",
                "Actualizado": "23/04/2026 12:00",
            }
        ]
    )

    report = build_inventory_difference_report_df(diff_df)

    assert "id" not in report.columns
    assert list(report.columns[:4]) == ["Código", "Producto", "Bodega", "Ubicación"]
    assert int(report.loc[0, "Dif. Stock"]) == -3
