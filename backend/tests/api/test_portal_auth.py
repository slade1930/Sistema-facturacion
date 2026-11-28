"""Pruebas del registro, login y sesiones del portal de empresas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogo import ClienteB2B
from app.models.seguridad import Cuenta, RolCuenta, Sesion

REGISTRO = {
    "nombre_empresa": "Empresa Portal Prueba",
    "ruc": "RUC-PORTAL-PRUEBA",
    "direccion": "Avenida Central",
    "telefono": "60001234",
    "correo": "portal@ejemplo.local",
    "sucursal": "Central",
    "contrasena": "Clave1234",
    "sector": "tecnologia",
}


@pytest.fixture
def db(client) -> Session:
    from app.db.session import get_db
    from app.main import app

    generador = app.dependency_overrides[get_db]()
    sesion = next(generador)
    try:
        yield sesion
    finally:
        generador.close()


def _registrar(client: TestClient, **cambios):
    datos = REGISTRO | cambios
    respuesta = client.post("/api/v1/auth/registro", json=datos)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_registro_crea_cliente_cuenta_y_sesion(client, db: Session):
    datos = _registrar(client)
    cliente = db.scalar(
        select(ClienteB2B).where(ClienteB2B.ruc == REGISTRO["ruc"])
    )
    cuenta = db.scalar(select(Cuenta).where(Cuenta.cliente_id == cliente.id))
    sesiones = db.scalars(
        select(Sesion).where(Sesion.cuenta_id == cuenta.id)
    ).all()

    assert datos["empresa"]["nombre"] == REGISTRO["nombre_empresa"]
    assert datos["empresa"]["sector"] == "tecnologia"
    assert cuenta.rol == RolCuenta.EMPRESA
    assert cuenta.debe_cambiar_clave is False
    assert len(sesiones) == 1
    from app.services.auth import hash_token

    assert sesiones[0].token_hash == hash_token(datos["token"])
    assert datos["debe_cambiar_clave"] is False


def test_login_con_nombre_de_empresa_y_clave(client):
    _registrar(client)
    respuesta = client.post(
        "/api/v1/auth/login",
        json={
            "nombre_empresa": REGISTRO["nombre_empresa"],
            "contrasena": REGISTRO["contrasena"],
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["token"]


def test_login_rechaza_clave_incorrecta(client):
    _registrar(client)
    respuesta = client.post(
        "/api/v1/auth/login",
        json={
            "nombre_empresa": REGISTRO["nombre_empresa"],
            "contrasena": "Incorrecta123",
        },
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "UNAUTHORIZED"


def test_clave_debe_tener_mayuscula_y_numero(client):
    respuesta = client.post(
        "/api/v1/auth/registro",
        json=REGISTRO | {"contrasena": "solo_minusculas", "ruc": "RUC-CLAVE-1"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "VALIDATION_ERROR"


def test_registro_rechaza_ruc_repetido(client):
    _registrar(client)
    respuesta = client.post(
        "/api/v1/auth/registro",
        json=REGISTRO | {"nombre_empresa": "Otra Empresa Portal"},
    )
    assert respuesta.status_code == 409


def test_logout_invalida_token(client):
    datos = _registrar(client)
    headers = {"Authorization": "Bearer " + datos["token"]}
    assert client.get("/api/v1/historial", headers=headers).status_code == 200
    salida = client.post("/api/v1/auth/logout", headers=headers)
    assert salida.status_code == 200
    assert client.get("/api/v1/historial", headers=headers).status_code == 401


def test_actor_sistema_con_api_key_no_tiene_cliente(client):
    assert client.get("/api/v1/historial").status_code == 200
    # /auth/yo exige una cuenta real; el actor sistema no la tiene.
    assert client.get("/api/v1/auth/yo").status_code == 401
