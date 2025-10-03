# tests/test_buscador_cp.py
import pandas as pd
import unicodedata
import pytest

# ---------- Utilidades de apoyo ----------

def df_preferente_header_1():
    # Simula tu Excel real: header en fila 2 visible => header=1 (0-based)
    # Columnas A:D
    return pd.DataFrame({
        "Comuna/Localidad": ["Algarrobo", "Alhué", "Alto Biobío"],
        "Provincia": ["San Antonio", "Melipilla", "Biobío"],
        "Region": ["Valparaiso", "Metropolitana de Santiago", "Biobio"],
        "Codigo Postal": ["2710000", "9650000", "4590000"],
    })

def df_header_2_columna_generica():
    # Caso donde header=2 da nombres genericos pero los datos están en filas siguientes
    return pd.DataFrame({
        "Columna1": ["Comuna/Localidad", "Algarrobo", "Alhué"],
        "Columna2": ["Provincia", "San Antonio", "Melipilla"],
        "Columna3": ["Region", "Valparaiso", "Metropolitana de Santiago"],
        "Columna4": ["Codigo Postal", "2710000", "9650000"],
    })

def df_sin_header_posicional():
    # Sin encabezado: 4 columnas que corresponden a COMUNA, PROVINCIA, REGIÓN, CP
    return pd.DataFrame([
        ["Algarrobo", "San Antonio", "Valparaiso", "2710000"],
        ["Alhué", "Melipilla", "Metropolitana de Santiago", "9650000"],
    ])

def df_inferencia_contenido():
    # Sin encabezado y sin claves claras, pero CP es la cuarta col numérica
    return pd.DataFrame([
        ["Foo", "Bar", "Valparaiso", "2710000"],
        ["Baz", "Qux", "Metropolitana de Santiago", "9650000"],
        ["Quillota", "Provincia X", "Valparaiso", "2260000"],
    ])

# ---------- Mocks de lectura Excel ----------

def make_read_excel_mock(switch):
    """
    Retorna una función que emula pandas.read_excel en base a 'switch':
    switch es un dict con claves (sheet_name, header, usecols|None) -> DataFrame
    Si no hay match exacto, intenta por (sheet_name, header) ignorando usecols.
    """
    def _mock_read_excel(path, sheet_name=0, header=0, dtype=None, engine=None, usecols=None, names=None, skiprows=None):
        key_full = (sheet_name, header, usecols)
        key_loose = (sheet_name, header)
        if key_full in switch:
            df = switch[key_full].copy()
        elif key_loose in switch:
            df = switch[key_loose].copy()
        else:
            # Por defecto, devuelve un DF vacío y dejará avanzar a otros respaldos
            return pd.DataFrame()

        # Si 'names' fue pedido (caso forzado A:D), reasignamos columnas
        if names is not None:
            df.columns = list(names)
        # Si hay skiprows, simulamos saltar n filas
        if skiprows:
            df = df.iloc[skiprows:, :].reset_index(drop=True)
        # Si usecols limita A:D, ya lo manejamos por el switch; aquí no es necesario
        return df
    return _mock_read_excel

# ---------- Tests ----------

def test_preferente_header_1(mod_buscador, inst, monkeypatch, fake_excel_file):
    """
    Caso real: header=1 y A:D con [Comuna/Localidad, Provincia, Region, Codigo Postal]
    Debe devolver columnas normalizadas REGIÓN, COMUNA, CÓDIGO POSTAL.
    """
    switch = {
        ("Hoja1", 1, "A:D"): df_preferente_header_1(),
    }
    monkeypatch.setattr(pd, "read_excel", make_read_excel_mock(switch))

    df = inst._leer_y_normalizar_excel(path=pd.Timestamp.now())  # path dummy
    assert list(df.columns) == ["REGIÓN", "COMUNA", "CÓDIGO POSTAL"]
    assert df.shape[0] == 3
    assert df.iloc[0]["COMUNA"] == "Algarrobo"
    assert df.iloc[0]["REGIÓN"].lower().startswith("valpar")  # Valparaiso
    assert df.iloc[0]["CÓDIGO POSTAL"] == "2710000"

def test_respaldo_header_2(mod_buscador, inst, monkeypatch, fake_excel_file):
    """
    Si el preferente falla, header=2 con datos alineados debe poder normalizar.
    """
    switch = {
        ("Hoja1", 1, "A:D"): pd.DataFrame(),  # fuerza fallo preferente
        ("Hoja1", 2): df_header_2_columna_generica(),
    }
    monkeypatch.setattr(pd, "read_excel", make_read_excel_mock(switch))

    df = inst._leer_y_normalizar_excel(path=object())  # path dummy
    # Debe haber detectado y normalizado por respaldo
    assert set(["REGIÓN", "COMUNA", "CÓDIGO POSTAL"]).issubset(df.columns)
    assert df.shape[0] >= 2

def test_respaldo_sin_header_posicional(mod_buscador, inst, monkeypatch, fake_excel_file):
    """
    Sin encabezado: asignación posicional COMUNA, PROVINCIA, REGIÓN, CÓDIGO POSTAL.
    """
    switch = {
        ("Hoja1", 1, "A:D"): pd.DataFrame(),  # preferente falla
        ("Hoja1", 2): pd.DataFrame(),         # header=2 falla
        ("Hoja1", 0): pd.DataFrame(),         # otros headers fallan
        ("Hoja1", 3): pd.DataFrame(),
        ("Hoja1", 4): pd.DataFrame(),
        ("Hoja1", 5): pd.DataFrame(),
        ("Hoja1", None): df_sin_header_posicional(),  # simulamos lectura sin header
    }

    def read_excel_mux(path, sheet_name=0, header=0, **kw):
        # Si header=None en pandas pasa como None. Pero nuestro mock usa key (sheet, None)
        # Aquí direccionamos: cuando header=None, usamos esa entrada; en otro caso, key normal.
        if header is None:
            return switch.get((sheet_name, None), pd.DataFrame())
        return switch.get((sheet_name, header), pd.DataFrame())

    monkeypatch.setattr(pd, "read_excel", read_excel_mux)

    # Parcheamos método interno que llama varias veces a read_excel sin header:
    # Nuestra implementación usa header=None en caminos “sin encabezado”, así que este mock lo cubre.
    df = inst._leer_y_normalizar_excel(path="dummy")
    assert list(df.columns) == ["REGIÓN", "COMUNA", "CÓDIGO POSTAL"]
    assert df.iloc[0]["COMUNA"] == "Algarrobo"
    assert df.iloc[0]["CÓDIGO POSTAL"] == "2710000"

def test_inferencia_por_contenido(mod_buscador, inst, monkeypatch, fake_excel_file):
    """
    Sin encabezado y sin claves evidentes, pero CP detectable por contenido.
    """
    switch = {
        ("Hoja1", 1, "A:D"): pd.DataFrame(),  # forzar camino inferencia
        ("Hoja1", 2): pd.DataFrame(),
        ("Hoja1", 0): pd.DataFrame(),
        ("Hoja1", 3): pd.DataFrame(),
        ("Hoja1", 4): pd.DataFrame(),
        ("Hoja1", 5): pd.DataFrame(),
        ("Hoja1", None): df_inferencia_contenido(),
    }

    def read_excel_mux(path, sheet_name=0, header=0, **kw):
        if header is None:
            return switch.get((sheet_name, None), pd.DataFrame())
        return switch.get((sheet_name, header), pd.DataFrame())

    monkeypatch.setattr(pd, "read_excel", read_excel_mux)

    df = inst._leer_y_normalizar_excel(path="dummy")
    assert set(["REGIÓN", "COMUNA", "CÓDIGO POSTAL"]).issubset(df.columns)
    # Valida que detectó CP como columna con valores numéricos de 7 dígitos
    assert all(df["CÓDIGO POSTAL"].str.len().between(4, 8))

def test_norm_text(mod_buscador, inst):
    assert inst._norm_text("  ÁlHuÉ  ") == "alhue"
    assert inst._norm_text("  REGIÓN  METROPOLITANA ") == "region metropolitana"

def test_error_si_no_detecta(mod_buscador, inst, monkeypatch, fake_excel_file):
    """
    Si todos los caminos fallan, debe lanzar ValueError con mensaje claro.
    """
    def always_empty(*args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_excel", always_empty)

    with pytest.raises(ValueError) as exc:
        inst._leer_y_normalizar_excel(path="no_importa")
    assert "No se pudieron detectar las columnas" in str(exc.value)

def test_synonyms_renames(mod_buscador, inst):
    """
    Verifica que _normalizar_columnas/_rename_soft detectan sinónimos.
    """
    df = pd.DataFrame({
        "código postal": ["1234567"],
        "comuna/localidad": ["Ñuñoa"],
        "región": ["Metropolitana"],
    })
    df2 = inst._normalizar_columnas(df)
    assert list(df2.columns) == ["CÓDIGO POSTAL", "COMUNA", "REGIÓN"] or \
           set(["REGIÓN", "COMUNA", "CÓDIGO POSTAL"]).issubset(df2.columns)
