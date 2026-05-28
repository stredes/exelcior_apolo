import pandas as pd

from app.gui.inventario_view import InventarioView


def make_view():
    return object.__new__(InventarioView)


def test_location_parts_do_not_merge_row_and_position_segments():
    view = make_view()

    assert view._extract_main_row("14-a1-a1") == "14"
    assert view._extract_letter_row("14-a1-a1") == "a"
    assert view._extract_position("14-a1-a1") == "a1"


def test_row_filter_matches_complete_progressive_sequence():
    view = make_view()
    locations = pd.Series(["14-a1-a1", "14-a1-b1", "14-a2-a1", "14-a2-b1", "15-a1-a1", "14-b1-a1"])

    mask = locations.apply(
        lambda value: view._extract_main_row(value) == "14"
        and view._location_row_matches(value, "a")
    )

    assert locations[mask].tolist() == ["14-a1-a1", "14-a1-b1", "14-a2-a1", "14-a2-b1"]


def test_position_filter_accepts_letter_number_or_complete_segment():
    view = make_view()

    assert view._location_position_matches("14-a1-b1", "b1")
    assert view._location_position_matches("14-a1-b1", "b")
    assert view._location_position_matches("14-a1-b1", "1")
    assert not view._location_position_matches("14-a1-b1", "a")


def test_location_sort_uses_warehouse_progressive_order():
    view = make_view()
    df = pd.DataFrame(
        {
            "Ubicacion": [
                "14-A1",
                "14-A6-A1",
                "14-A10",
                "14-A2-A1",
                "14-A2-B1",
                "14-A3-A1",
                "14-A5",
                "14-A12",
                "14-A11",
                "14-A4-B1",
                "14-A4-A1",
            ]
        }
    )

    sorted_df = view._sorted_dataframe(df, "Ubicacion", True)

    assert sorted_df["Ubicacion"].tolist() == [
        "14-A1",
        "14-A2-A1",
        "14-A2-B1",
        "14-A3-A1",
        "14-A4-A1",
        "14-A4-B1",
        "14-A5",
        "14-A6-A1",
        "14-A10",
        "14-A11",
        "14-A12",
    ]
