"""X-Forwarded-For, errores y logs sin secretos."""

import logging
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import deps
from app.services import auth as servicio_auth

EMPRESA_XFF = "Empresa XFF Endurecimiento"
EMPRESA_ERRORES = "Empresa Errores Endurecimiento"
CLAVE_PRUEBA = "Clave1234"
CLAVE_INCORRECTA = "clave-incorrecta"
IP_FUENTE = "203.0.113.10"
IP_OTRA = "203.0.113.11"
IP_LOCAL = "testclient"


def _peticion(ip_remitente: str) -> SimpleNamespace:
    return SimpleNamespace(
        headers={"X-Forwarded-For": ip_remitente},
        client=SimpleNamespace(host=IP_LOCAL),
    )


@pytest.fixture(autouse=True)
def _iteraciones_rapidas(monkeypatch: pytest.MonkeyPatch):
    # El objetivo es la IP del límite, no el coste del hash.
    monkeypatch.setattr(servicio_auth, "_iteraciones", lambda: 1_000)


def test_endurecimiento_ip_para_limite_ignora_xff_sin_api_key_valida(
    monkeypatch: pytest.MonkeyPatch,
):
    peticion = _peticion(IP_FUENTE)
    clave_valida = os.environ.get("API_KEY", "")

    assert deps.ip_para_limite(peticion, CLAVE_INCORRECTA) == IP_LOCAL
    assert deps.ip_para_limite(peticion, "") == IP_LOCAL
    assert deps.ip_para_limite(peticion, clave_valida) == IP_FUENTE


def test_endurecimiento_limite_login_ignora_xff_sin_api_key_valida(client: TestClient):
    cuerpo = {"nombre_empresa": EMPRESA_XFF, "contrasena": CLAVE_PRUEBA}
    nombre = servicio_auth.normalizar_nombre_usuario(EMPRESA_XFF)
    try:
        for _ in range(5):
            respuesta = client.post(
                "/api/v1/auth/login",
                json=cuerpo,
                headers={
                    "X-API-Key": CLAVE_INCORRECTA,
                    "X-Forwarded-For": IP_FUENTE,
                },
            )
            assert respuesta.status_code == 401, respuesta.text

        otra_ip = client.post(
            "/api/v1/auth/login",
            json={"nombre_empresa": EMPRESA_XFF, "contrasena": CLAVE_PRUEBA},
            headers={
                "X-API-Key": CLAVE_INCORRECTA,
                "X-Forwarded-For": IP_OTRA,
            },
        )

        # Si se hubiera creído la cabecera, esta IP nueva no estaría bloqueada.
        assert otra_ip.status_code == 429
        assert otra_ip.headers["retry-after"]
    finally:
        for ip in (IP_LOCAL, IP_FUENTE, IP_OTRA):
            servicio_auth.limpiar_intentos(ip, nombre)


def test_endurecimiento_errores_no_devuelven_secretos_ni_trazas(
    client: TestClient, caplog: pytest.LogCaptureFixture
):
    cuerpo = {
        "nombre_empresa": EMPRESA_ERRORES,
        "contrasena": {"valor": CLAVE_PRUEBA},
    }

    with caplog.at_level(logging.WARNING):
        respuesta = client.post("/api/v1/auth/login", json=cuerpo)

    assert respuesta.status_code == 422
    assert CLAVE_PRUEBA not in respuesta.text
    assert "Traceback" not in respuesta.text
    assert "SELECT" not in respuesta.text.upper()
    errores = respuesta.json()["errors"]
    assert errores
    assert all("input" not in error for error in errores)
    assert all("ctx" not in error for error in errores)
    assert CLAVE_PRUEBA not in caplog.text


def test_endurecimiento_logs_no_registran_api_key_rechazada(
    client: TestClient, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.WARNING):
        respuesta = client.get(
            "/api/v1/historial", headers={"X-API-Key": CLAVE_INCORRECTA}
        )

    assert respuesta.status_code == 401
    assert CLAVE_INCORRECTA not in caplog.text
