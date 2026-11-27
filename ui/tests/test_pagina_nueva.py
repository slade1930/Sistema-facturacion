import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.facturacion.nueva import construir_payload, crear, obtener_pdf
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_construir_payload_mapea_cliente_y_lineas():
    datos = {
        "cliente_nombre": "  Cliente Prueba  ",
        "cliente_ruc": "  RUC-123  ",
        "mostrar_ruc": False,
        "fecha": "2026-11-27",
        "condicion_pago": "credito",
        "portes": "1.50",
        "cliente_direccion": "  ",
        "notas": "  Nota  ",
    }
    lineas = [
        {
            "descripcion": "  Servicio  ",
            "cantidad": "2",
            "precio_unitario": "3.50",
            "precio_unidad": None,
            "descuento_pct": "10",
            "gravada": False,
            "unidades_por_caja": "1",
            "cobrar_por": "caja",
        }
    ]

    payload = construir_payload(datos, lineas)

    assert payload["cliente_nombre"] == "Cliente Prueba"
    assert payload["cliente_ruc"] == "RUC-123"
    assert payload["mostrar_ruc"] is False
    assert payload["fecha"] == "2026-11-27"
    assert payload["condicion_pago"] == "credito"
    assert payload["portes"] == "1.50"
    assert payload["cliente_direccion"] is None
    assert payload["notas"] == "Nota"
    assert payload["lineas"][0]["orden"] == 1
    assert payload["lineas"][0]["descripcion"] == "Servicio"
    assert payload["lineas"][0]["cantidad"] == "2"
    assert payload["lineas"][0]["precio_unidad"] is None
    assert payload["lineas"][0]["gravada"] is False
    assert payload["lineas"][0]["cobrar_por"] == "caja"


def test_crear_envia_post_con_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        vistos["cuerpo"] = json.loads(solicitud.content)
        return httpx.Response(201, json={"id": 1, "numero_serie": "FAC-2026-0001"})

    payload = construir_payload(
        {"cliente_nombre": "Cliente", "condicion_pago": "contado"},
        [{"descripcion": "Item", "cantidad": "1", "precio_unitario": "5"}],
    )

    with crear_cliente(manejador) as cliente_api:
        factura = crear(cliente_api, payload)

    assert factura["numero_serie"] == "FAC-2026-0001"
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/facturas"
    assert vistos["api_key"] == "clave-de-prueba"
    assert vistos["cuerpo"] == payload


def test_crear_422_expone_errores():
    cuerpo = {
        "detail": "Datos de entrada inválidos.",
        "code": "VALIDATION_ERROR",
        "errors": [
            {"loc": ["body", "cliente_nombre"], "msg": "Field required"},
            {"loc": ["body", "lineas"], "msg": "List should have at least 1 item"},
        ],
    }

    def manejador(solicitud):
        return httpx.Response(422, json=cuerpo)

    with crear_cliente(manejador) as cliente_api:
        try:
            crear(cliente_api, {})
        except ErrorApi as error:
            assert error.status_code == 422
            assert error.code == "VALIDATION_ERROR"
            assert error.errors == cuerpo["errors"]
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_obtener_pdf_devuelve_bytes():
    def manejador(solicitud):
        return httpx.Response(
            200,
            content=b"%PDF-1.4",
            headers={"Content-Type": "application/pdf"},
        )

    with crear_cliente(manejador) as cliente_api:
        contenido = obtener_pdf(cliente_api, 7)

    assert contenido == b"%PDF-1.4"
