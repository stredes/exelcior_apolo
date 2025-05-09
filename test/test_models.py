from datetime import datetime

import pytest
from app.db.models import (Base, Configuracion, HistorialArchivo,
                           RegistroImpresion, User)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_create_user(session):
    user = User(nombre="Test", email="test@example.com", password="123456")
    session.add(user)
    session.commit()
    assert user.id is not None


def test_create_configuracion(session):
    config = Configuracion(usuario_id=1, clave="modo", valor="fedex")
    session.add(config)
    session.commit()
    assert config.id is not None


def test_create_historial(session):
    historial = HistorialArchivo(
        usuario_id=1, nombre_archivo="archivo.xlsx", modo_utilizado="urbano"
    )
    session.add(historial)
    session.commit()
    assert historial.id is not None


def test_create_impresion(session):
    imp = RegistroImpresion(usuario_id=1, archivo_impreso="export.pdf")
    session.add(imp)
    session.commit()
    assert imp.id is not None
