"""Cabeceras de seguridad y CORS sin comodín."""

import pytest
from fastapi.testclient import TestClient

from app.core.cabeceras import CORS_ORIGINS_ENV

ORIGEN_PERMITIDO = "https://portal.example.com"


def test_endurecimiento_cabeceras_seguridad_en_respuestas_y_errores(client):
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert respuesta.headers["x-frame-options"] == "DENY"
    assert respuesta.headers["referrer-policy"] == "no-referrer"

    error = client.post("/api/v1/auth/login", json={})

    assert error.status_code == 422
    assert error.headers["cache-control"] == "no-store"
    assert error.headers["x-content-type-options"] == "nosniff"


def test_endurecimiento_cors_sin_comodin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(
        CORS_ORIGINS_ENV, f"{ORIGEN_PERMITIDO}, https://admin.example.com, *"
    )

    permitida = client.get("/health", headers={"Origin": ORIGEN_PERMITIDO})

    assert permitida.status_code == 200
    assert permitida.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO
    assert "Origin" in permitida.headers.get("vary", "")

    rechazada = client.get("/health", headers={"Origin": "https://externo.example.com"})

    assert rechazada.status_code == 200
    assert "access-control-allow-origin" not in rechazada.headers

    comodin = client.get("/health", headers={"Origin": "*"})

    assert "access-control-allow-origin" not in comodin.headers
    assert all(
        valor != "*"
        for clave, valor in permitida.headers.items()
        if "access-control" in clave.lower()
    )


def test_endurecimiento_cors_preflight_solo_origenes_explicitos(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(CORS_ORIGINS_ENV, ORIGEN_PERMITIDO)

    preflight = client.options(
        "/health",
        headers={
            "Origin": ORIGEN_PERMITIDO,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )

    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO
    assert "GET" in preflight.headers["access-control-allow-methods"]
    assert "X-API-Key" in preflight.headers["access-control-allow-headers"]

    sin_origen = client.options(
        "/health",
        headers={
            "Origin": "https://externo.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in sin_origen.headers
