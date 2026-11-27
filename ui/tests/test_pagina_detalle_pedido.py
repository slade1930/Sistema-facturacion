import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.pedidos.detalle_pedido import obtener_pedido, resumen_lineas
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_obtener_pedido_envia_get_y_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(200, json={"id": 7, "estado": "pendiente"})

    with crear_cliente(manejador) as cliente_api:
        pedido = obtener_pedido(cliente_api, 7)

    assert pedido["id"] == 7
    assert vistos["metodo"] == "GET"
    assert vistos["ruta"] == "/api/v1/pedidos/7"
    assert vistos["api_key"] == "clave-de-prueba"


def test_obtener_pedido_inexistente_es_404():
    def manejador(solicitud):
        return httpx.Response(
            404, json={"detail": "Pedido no encontrado.", "code": "NOT_FOUND"}
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            obtener_pedido(cliente_api, 99)
        except ErrorApi as error:
            assert error.status_code == 404
            assert error.code == "NOT_FOUND"
            assert error.detail == "Pedido no encontrado."
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_resumen_lineas_etiqueta_presentaciones_y_orden():
    pedido = {
        "lineas": [
            {
                "orden": 2,
                "producto_id": 3,
                "tipo_empaque": "media_caja",
                "cantidad": "4.00",
                "subtotal": "12.00",
            },
            {
                "orden": 1,
                "producto_id": 1,
                "tipo_empaque": "unidad",
                "cantidad": "2.00",
                "subtotal": "1.00",
            },
        ]
    }

    lineas = resumen_lineas(pedido)

    assert lineas == [
        {
            "orden": "2",
            "producto_id": "3",
            "presentacion": "Media caja",
            "cantidad": "4.00",
            "subtotal": "12.00",
        },
        {
            "orden": "1",
            "producto_id": "1",
            "presentacion": "Unidad",
            "cantidad": "2.00",
            "subtotal": "1.00",
        },
    ]


def test_resumen_lineas_con_empaque_desconocido():
    pedido = {
        "lineas": [
            {
                "orden": 1,
                "producto_id": 5,
                "tipo_empaque": "otro",
                "cantidad": "1.00",
                "subtotal": "5.00",
            }
        ]
    }

    lineas = resumen_lineas(pedido)

    assert lineas[0]["presentacion"] == "otro"
    assert resumen_lineas({}) == []
