# tests/conftest.py
import os
import sys
import pytest
from pathlib import Path

# Asegura que el paquete "app" esté disponible en los tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _no_real_print_env(monkeypatch, tmp_path):
    """
    Evita cualquier impresión real en entornos donde se usen herramientas del SO.
    """
    # Redirige variables de impresión si tu código las usara
    monkeypatch.setenv("EXCELCIOR_PRINTER", "TestPrinter")
    monkeypatch.setenv("EXCELCIOR_PRINT_TIMEOUT", "3")
    yield
