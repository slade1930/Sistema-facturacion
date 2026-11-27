import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.verificar.verificar import consultar
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_consultar_verificacion_no_envia_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["url"] = str(solicitud.url)
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(
            200,
            json={
                "valida": True,
                "numero_serie": "FAC-2026-0001",
                "codigo_verificacion": "abc123",
                "fecha": "2026-11-27",
                "cliente_nombre": "Cliente Prueba",
                "total": "10.50",
                "estado": "emitida",
            },
        )

    with crear_cliente(manejador) as cliente:
        datos = consultar(cliente, "FAC-2026-0001", "abc123")

    assert datos["valida"] is True
    assert datos["cliente_nombre"] == "Cliente Prueba"
    assert vistos["url"].endswith("/api/v1/verificar/FAC-2026-0001/abc123")
    assert vistos["api_key"] is None


def test_consultar_verificacion_404_es_not_found():
    def manejador(solicitud):
        return httpx.Response(
            404,
            json={
                "detail": "No se encontró una factura con ese número y código de verificación.",
                "code": "NOT_FOUND",
            },
        )

    with crear_cliente(manejador) as cliente:
        try:
            consultar(cliente, "FAC-2026-0001", "malo")
        except ErrorApi as error:
            assert error.status_code == 404
            assert error.code == "NOT_FOUND"
            assert "No se encontró" in error.detail
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_consultar_verificacion_422_expone_errores():
    cuerpo = {
        "detail": "Datos de entrada inválidos.",
        "code": "VALIDATION_ERROR",
        "errors": [
            {"loc": ["path", "numero_serie"], "msg": "Field required"},
        ],
    }

    def manejador(solicitud):
        return httpx.Response(422, json=cuerpo)

    with crear_cliente(manejador) as cliente:
        try:
            consultar(cliente, "", "abc123")
        except ErrorApi as error:
            assert error.code == "VALIDATION_ERROR"
            assert error.errors == cuerpo["errors"]
        else:
            raise AssertionError("Se esperaba ErrorApi")
