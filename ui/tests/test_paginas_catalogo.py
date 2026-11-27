import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.catalogo.carrito import calcular, leer_carrito, lineas_para_calculo
from pages.catalogo.catalogo import agregar_al_carrito, listar_productos
from state.cliente_api import ClienteApi, ErrorApi


class Widget:
    def __init__(self, valor):
        self.value = valor


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_listar_productos_envia_filtros_y_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["ruta"] = solicitud.url.path
        vistos["params"] = dict(solicitud.url.params)
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(200, json=[])

    with crear_cliente(manejador) as cliente_api:
        listar_productos(cliente_api, "leche", 3)

    assert vistos["ruta"] == "/api/v1/productos"
    assert vistos["params"]["busqueda"] == "leche"
    assert vistos["params"]["categoria_id"] == "3"
    assert vistos["api_key"] == "clave-de-prueba"


def test_agregar_al_carrito_suma_y_crea():
    carrito = []
    producto = {"id": 1, "nombre": "Leche"}

    agregar_al_carrito(carrito, producto, "caja", 2)
    agregar_al_carrito(carrito, producto, "caja", 3)
    agregar_al_carrito(carrito, producto, "unidad", 1)

    assert len(carrito) == 2
    assert carrito[0]["cantidad"] == 5.0
    assert carrito[1]["tipo_empaque"] == "unidad"
    assert carrito[1]["cantidad"] == 1.0


def test_lineas_para_calculo_quita_campos_de_ui():
    carrito = [
        {
            "producto_id": 1,
            "nombre": "Leche",
            "tipo_empaque": "caja",
            "cantidad": 2.0,
            "_envase": Widget("caja"),
        }
    ]

    assert lineas_para_calculo(carrito) == [
        {"producto_id": 1, "tipo_empaque": "caja", "cantidad": "2.0"}
    ]


def test_leer_carrito_toma_valores_de_los_widgets():
    carrito = [
        {
            "producto_id": 1,
            "nombre": "Leche",
            "tipo_empaque": "caja",
            "cantidad": 2.0,
            "_envase": Widget("unidad"),
            "_cantidad": Widget(4.0),
        }
    ]

    leido = leer_carrito(carrito)

    assert leido[0]["tipo_empaque"] == "unidad"
    assert leido[0]["cantidad"] == 4.0


def test_calcular_envia_post_y_devuelve_totales():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["cuerpo"] = json.loads(solicitud.content)
        return httpx.Response(
            200,
            json={
                "lineas": [],
                "subtotal": "10.00",
                "descuento_total": "0.00",
                "base_gravada": "10.00",
                "base_exenta": "0.00",
                "itbms": "0.70",
                "total": "10.70",
            },
        )

    carrito = [
        {
            "producto_id": 1,
            "nombre": "Leche",
            "tipo_empaque": "caja",
            "cantidad": 2.0,
        }
    ]

    with crear_cliente(manejador) as cliente_api:
        datos = calcular(cliente_api, carrito)

    assert datos["total"] == "10.70"
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/carrito/calcular"
    assert vistos["cuerpo"] == {
        "lineas": [{"producto_id": 1, "tipo_empaque": "caja", "cantidad": "2.0"}]
    }


def test_calcular_producto_inexistente_es_404():
    def manejador(solicitud):
        return httpx.Response(
            404,
            json={"detail": "Producto no encontrado: 9.", "code": "NOT_FOUND"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            calcular(cliente_api, [{"producto_id": 9, "tipo_empaque": "caja", "cantidad": 1}])
        except ErrorApi as error:
            assert error.status_code == 404
            assert error.code == "NOT_FOUND"
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_calcular_producto_inactivo_es_422():
    def manejador(solicitud):
        return httpx.Response(
            422,
            json={"detail": "El producto 'Leche' no está activo.", "code": "VALIDATION_ERROR"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            calcular(cliente_api, [{"producto_id": 1, "tipo_empaque": "caja", "cantidad": 1}])
        except ErrorApi as error:
            assert error.status_code == 422
            assert error.code == "VALIDATION_ERROR"
        else:
            raise AssertionError("Se esperaba ErrorApi")
