import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.facturacion.detalle import anular, duplicar, obtener, obtener_pdf
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_obtener_envia_api_key_y_devuelve_factura():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(
            200,
            json={"id": 1, "numero_serie": "FAC-2026-0001", "estado": "emitida"},
        )

    with crear_cliente(manejador) as cliente_api:
        factura = obtener(cliente_api, 1)

    assert factura["numero_serie"] == "FAC-2026-0001"
    assert vistos["metodo"] == "GET"
    assert vistos["ruta"] == "/api/v1/facturas/1"
    assert vistos["api_key"] == "clave-de-prueba"


def test_obtener_404_es_not_found():
    def manejador(solicitud):
        return httpx.Response(
            404,
            json={"detail": "Factura no encontrada.", "code": "NOT_FOUND"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            obtener(cliente_api, 99)
        except ErrorApi as error:
            assert error.status_code == 404
            assert error.code == "NOT_FOUND"
            assert error.detail == "Factura no encontrada."
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_anular_dos_veces_es_conflict():
    def manejador(solicitud):
        return httpx.Response(
            409,
            json={"detail": "La factura ya está anulada.", "code": "CONFLICT"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            anular(cliente_api, 1)
        except ErrorApi as error:
            assert error.status_code == 409
            assert error.code == "CONFLICT"
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_duplicar_hace_post():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        return httpx.Response(
            201,
            json={"id": 2, "numero_serie": "FAC-2026-0002", "estado": "emitida"},
        )

    with crear_cliente(manejador) as cliente_api:
        nueva = duplicar(cliente_api, 1)

    assert nueva["id"] == 2
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/facturas/1/duplicar"


def test_obtener_pdf_devuelve_bytes():
    def manejador(solicitud):
        return httpx.Response(
            200,
            content=b"%PDF-1.4",
            headers={"Content-Type": "application/pdf"},
        )

    with crear_cliente(manejador) as cliente_api:
        contenido = obtener_pdf(cliente_api, 1)

    assert contenido == b"%PDF-1.4"
