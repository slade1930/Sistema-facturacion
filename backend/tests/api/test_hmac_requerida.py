"""Pruebas de la FACTURA_HMAC_KEY obligatoria al arrancar."""

import importlib
import sys

import pytest

from app.core.config import validar_factura_hmac_key


def test_validar_hmac_falla_sin_variable(monkeypatch):
    monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)

    with pytest.raises(RuntimeError, match="FACTURA_HMAC_KEY no está configurada"):
        validar_factura_hmac_key()


def test_app_no_arranca_sin_hmac(monkeypatch):
    monkeypatch.setenv("API_KEY", "api-key-de-prueba-api")
    monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)
    sys.modules.pop("app.main", None)

    with pytest.raises(RuntimeError, match="FACTURA_HMAC_KEY no está configurada"):
        importlib.import_module("app.main")
