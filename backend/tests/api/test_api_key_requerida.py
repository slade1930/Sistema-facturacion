"""Pruebas de la API_KEY obligatoria al arrancar y en cada petición."""

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from app.core.config import validar_api_key


def test_validar_api_key_falla_sin_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin API_KEY la validación debe fallar, sin mostrar valores."""
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="API_KEY no está configurada"):
        validar_api_key()


def test_app_no_arranca_sin_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importar app.main sin API_KEY debe fallar antes de crear la app."""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)
    sys.modules.pop("app.main", None)

    with pytest.raises(RuntimeError, match="API_KEY no está configurada"):
        importlib.import_module("app.main")


def test_sin_clave_en_header_se_rechaza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Una petición sin X-API-Key debe dar 401."""
    monkeypatch.setenv("API_KEY", "api-key-de-prueba-api")
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-hmac-de-prueba-api")
    sys.modules.pop("app.main", None)
    app = importlib.import_module("app.main").app

    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/v1/categorias", headers={"X-API-Key": ""})

    assert respuesta.status_code == 401
