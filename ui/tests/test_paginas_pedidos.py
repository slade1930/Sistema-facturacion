import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.pedidos.convertir_a_factura import facturar, obtener_pedido
from pages.pedidos.pedidos_pendientes import (
    calcular_paginacion,
    listar_pendientes,
)
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_listar_pendientes_envia_limite_y_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["ruta"] = solicitud.url.path
        vistos["params"] = dict(solicitud.url.params)
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "cliente_id": 3,
                    "estado": "pendiente",
                    "total_estimado": "10.50",
                    "notas": None,
                    "factura_generada_id": None,
                    "lineas": [],
                }
            ],
        )

    with crear_cliente(manejador) as cliente_api:
        pedidos = listar_pendientes(cliente_api, 50)

    assert pedidos[0]["id"] == 1
    assert vistos["ruta"] == "/api/v1/pedidos/por-facturar"
    assert vistos["params"]["limite"] == "50"
    assert vistos["api_key"] == "clave-de-prueba"


def test_obtener_pedido_404():
    def manejador(solicitud):
        return httpx.Response(
            404,
            json={"detail": "Pedido no encontrado.", "code": "NOT_FOUND"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            obtener_pedido(cliente_api, 99)
        except ErrorApi as error:
            assert error.status_code == 404
            assert error.code == "NOT_FOUND"
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_facturar_envia_post_y_devuelve_factura():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        return httpx.Response(
            201,
            json={"id": 5, "numero_serie": "FAC-2026-0005", "total": "10.50"},
        )

    with crear_cliente(manejador) as cliente_api:
        factura = facturar(cliente_api, 1)

    assert factura["numero_serie"] == "FAC-2026-0005"
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/pedidos/1/facturar"


def test_facturar_dos_veces_es_conflict():
    def manejador(solicitud):
        return httpx.Response(
            409,
            json={"detail": "El pedido ya fue facturado.", "code": "CONFLICT"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            facturar(cliente_api, 1)
        except ErrorApi as error:
            assert error.status_code == 409
            assert error.code == "CONFLICT"
            assert error.detail == "El pedido ya fue facturado."
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_facturar_pedido_cancelado_es_422():
    def manejador(solicitud):
        return httpx.Response(
            422,
            json={
                "detail": "Un pedido cancelado no se puede facturar.",
                "code": "VALIDATION_ERROR",
            },
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            facturar(cliente_api, 2)
        except ErrorApi as error:
            assert error.status_code == 422
            assert error.code == "VALIDATION_ERROR"
            assert error.detail == "Un pedido cancelado no se puede facturar."
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_paginacion_sin_pedidos():
    assert calcular_paginacion(0, 1) == (1, 0, 0)


def test_paginacion_con_20_pedidos():
    assert calcular_paginacion(20, 1) == (1, 0, 20)


def test_paginacion_con_21_pedidos():
    assert calcular_paginacion(21, 1) == (1, 0, 20)
    assert calcular_paginacion(21, 2) == (2, 20, 21)


def test_paginacion_con_40_pedidos():
    assert calcular_paginacion(40, 2) == (2, 20, 40)


def test_paginacion_con_41_pedidos():
    assert calcular_paginacion(41, 3) == (3, 40, 41)


def test_paginacion_limita_pagina_fuera_de_rango():
    assert calcular_paginacion(41, 5) == (3, 40, 41)
    assert calcular_paginacion(41, 0) == (1, 0, 20)
