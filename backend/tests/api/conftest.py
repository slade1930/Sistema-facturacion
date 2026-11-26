"""Gente, acá va la fixture que van a usar las pruebas de los endpoints."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db, get_engine


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    # Gente, si la app necesita la clave HMAC para arrancar, la tomamos del entorno.
    # Si no está, le ponemos una de prueba nomás, sin mostrarla por ningún lado.
    monkeypatch.setenv(
        "FACTURA_HMAC_KEY",
        os.environ.get("FACTURA_HMAC_KEY") or "clave-hmac-de-prueba-api",
    )
    # Gente, clave fija de prueba; la app ya no trae ninguna por defecto.
    api_key = "api-key-de-prueba-api"
    monkeypatch.setenv("API_KEY", api_key)

    # Impórtala recién acá para que ya tenga el entorno listo.
    from app.main import app

    # Gente, usamos la base del compose (get_engine ya lee DATABASE_URL del entorno).
    # La conexión queda dentro de una transacción grande y al final le hacemos rollback.
    connection = get_engine().connect()
    transaccion = connection.begin()

    # Con create_savepoint los endpoints pueden hacer db.commit() nomás,
    # ese commit libera el savepoint pero no cierra la transacción de afuera.
    sesion = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db() -> Generator[Session, None, None]:
        # Gente, siempre damos la misma sesión para que el test limpie todo junto.
        try:
            yield sesion
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app, headers={"X-API-Key": api_key}) as cliente:
            yield cliente
    finally:
        # Gente, devolvemos la app como estaba y tiramos todo lo que hizo el test.
        app.dependency_overrides.clear()
        sesion.close()
        transaccion.rollback()
        connection.close()
