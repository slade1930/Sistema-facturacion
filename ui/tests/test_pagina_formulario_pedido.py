import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.pedidos.formulario_pedido import (
    construir_lineas,
    construir_pedido,
    crear_pedido,
    listar_clientes,
)
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_listar_clientes_envia_solo_activos_y_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["ruta"] = solicitud.url.path
        vistos["params"] = dict(solicitud.url.params)
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(200, json=[])

    with crear_cliente(manejador) as cliente_api:
        listar_clientes(cliente_api, "Acme")

    assert vistos["ruta"] == "/api/v1/clientes"
    assert vistos["params"]["solo_activos"] == "true"
    assert vistos["params"]["busqueda"] == "Acme"
    assert vistos["api_key"] == "clave-de-prueba"


def test_construir_lineas_toma_subtotal_del_backend():
    carrito = [
        {"producto_id": 1, "nombre": "Leche", "tipo_empaque": "caja", "cantidad": 2.0},
        {"producto_id": 2, "nombre": "Pan", "tipo_empaque": "unidad", "cantidad": 3.0},
    ]
    calculo = {
        "lineas": [
            {"producto_id": 2, "tipo_empaque": "unidad", "subtotal": "1.50"},
            {"producto_id": 1, "tipo_empaque": "caja", "subtotal": "10.00"},
        ]
    }

    lineas = construir_lineas(carrito, calculo)

    assert lineas == [
        {
            "producto_id": 1,
            "tipo_empaque": "caja",
            "cantidad": "2.0",
            "subtotal": "10.00",
            "orden": 1,
        },
        {
            "producto_id": 2,
            "tipo_empaque": "unidad",
            "cantidad": "3.0",
            "subtotal": "1.50",
            "orden": 2,
        },
    ]


def test_construir_lineas_falla_si_falta_calculo():
    carrito = [
        {"producto_id": 1, "nombre": "Leche", "tipo_empaque": "caja", "cantidad": 2.0}
    ]

    with pytest.raises(ValueError, match="No hay precio calculado"):
        construir_lineas(carrito, {"lineas": []})


def test_construir_pedido_usa_subtotal_como_estimado():
    carrito = [
        {"producto_id": 1, "nombre": "Leche", "tipo_empaque": "caja", "cantidad": 2.0}
    ]
    calculo = {
        "subtotal": "10.00",
        "total": "10.70",
        "lineas": [
            {"producto_id": 1, "tipo_empaque": "caja", "subtotal": "10.00"}
        ],
    }

    pedido = construir_pedido(3, "  Nota  ", carrito, calculo)

    assert pedido["cliente_id"] == 3
    assert pedido["estado"] == "pendiente"
    assert pedido["total_estimado"] == "10.00"
    assert pedido["notas"] == "Nota"
    assert pedido["lineas"][0]["subtotal"] == "10.00"


def test_crear_pedido_envia_post():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["cuerpo"] = json.loads(solicitud.content)
        return httpx.Response(
            201,
            json={"id": 5, "cliente_id": 3, "estado": "pendiente"},
        )

    payload = {"cliente_id": 3, "estado": "pendiente", "lineas": []}

    with crear_cliente(manejador) as cliente_api:
        pedido = crear_pedido(cliente_api, payload)

    assert pedido["id"] == 5
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/pedidos"
    assert vistos["cuerpo"] == payload


def test_crear_pedido_conflicto_es_409():
    def manejador(solicitud):
        return httpx.Response(
            409,
            json={"detail": "El pedido ya existe.", "code": "CONFLICT"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            crear_pedido(cliente_api, {})
        except ErrorApi as error:
            assert error.status_code == 409
            assert error.code == "CONFLICT"
        else:
            raise AssertionError("Se esperaba ErrorApi")
