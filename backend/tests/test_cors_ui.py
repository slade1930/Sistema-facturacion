import os

os.environ.setdefault("API_KEY", "api-key-de-prueba")
os.environ.setdefault("FACTURA_HMAC_KEY", "hmac-de-prueba")
os.environ.setdefault("UI_ORIGIN", "http://localhost:8080")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_preflight_cors_para_nicegui():
    respuesta = client.options(
        "/api/v1/productos",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:8080"
    assert "X-API-Key" in respuesta.headers["access-control-allow-headers"]