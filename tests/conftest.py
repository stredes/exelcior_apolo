# tests/conftest.py
import builtins
import types
import pandas as pd
import pytest

@pytest.fixture
def mod_buscador():
    """
    Importa el módulo del buscador una sola vez para los tests.
    """
    import importlib
    mod = importlib.import_module("app.gui.buscador_codigos_postales")
    return mod

@pytest.fixture
def inst(mod_buscador):
    """
    Crea una instancia 'vacía' sin ejecutar __init__ para poder
    testear métodos internos sin lanzar la GUI ni hilos.
    """
    cls = mod_buscador.BuscadorCodigosPostales
    obj = object.__new__(cls)
    # Atributos mínimos que usan los métodos
    obj.COLS_TARGET = ("REGIÓN", "COMUNA", "CÓDIGO POSTAL")
    obj.COL_SYNONYMS = cls.COL_SYNONYMS
    obj.PREFERRED_HEADER_ROWS = cls.PREFERRED_HEADER_ROWS
    return obj

class FakeExcelFile:
    def __init__(self, path, engine=None):
        self.path = path
        self.engine = engine
        # emula 1 sola hoja por defecto
        self.sheet_names = ["Hoja1"]

@pytest.fixture
def fake_excel_file(monkeypatch):
    """
    Parcha pandas.ExcelFile para evitar leer archivos reales.
    """
    monkeypatch.setattr(pd, "ExcelFile", FakeExcelFile)
    return FakeExcelFile
