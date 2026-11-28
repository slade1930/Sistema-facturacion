import json
import sys
from pathlib import Path

import httpx
import pytest
from nicegui import app, ui
from nicegui.testing import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.catalogo import carrito, catalogo
from state.cliente_api import ClienteApi, ErrorApi


MENSAJE_CONEXION = (
    "No pudimos conectar con el sistema. Revisa tu conexión e inténtalo de nuevo."
)
CARRITO_VACIO = "Tu carrito está vacío. Añade productos desde el catálogo"
TOTALES = {
    "lineas": [
        {
            "producto_id": 1,
            "descripcion": "Leche",
            "tipo_empaque": "caja",
            "cantidad": "2.00",
            "precio_unitario": "12.50",
            "subtotal": "25.00",
        }
    ],
    "subtotal": "25.00",
    "descuento_total": "0.00",
    "base_gravada": "25.00",
    "base_exenta": "0.00",
    "itbms": "1.75",
    "total": "26.75",
}
PRODUCTO = {
    "id": 1,
    "nombre": "Leche",
    "sku": "LE-1",
    "precio_caja": "12.50",
    "precio_unidad": "1.25",
    "precio_media_caja": "6.25",
    "permite_media_caja": True,
    "estado_activo": True,
}


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_orq_carrito_agrupa_por_producto_y_presentacion():
    carrito_actual = []

    catalogo.agregar_al_carrito(carrito_actual, PRODUCTO, "caja", 2)
    catalogo.agregar_al_carrito(carrito_actual, PRODUCTO, "caja", 1)
    catalogo.agregar_al_carrito(carrito_actual, PRODUCTO, "media_caja", 3)

    assert len(carrito_actual) == 2
    assert carrito_actual[0]["cantidad"] == 3.0
    assert carrito_actual[1]["tipo_empaque"] == "media_caja"


def test_orq_carrito_media_caja_solo_si_el_producto_la_permite():
    permitido = catalogo.opciones_empaque(PRODUCTO)
    sin_media = {**PRODUCTO, "permite_media_caja": False}

    assert "media_caja" in permitido
    assert "media_caja" not in catalogo.opciones_empaque(sin_media)
    assert "caja" in catalogo.opciones_empaque(sin_media)


def test_orq_carrito_lineas_para_calculo_usan_texto_decimal():
    lineas = carrito.lineas_para_calculo(
        [{"producto_id": 1, "tipo_empaque": "caja", "cantidad": 2.0}]
    )

    assert lineas == [
        {"producto_id": 1, "tipo_empaque": "caja", "cantidad": "2.0"}
    ]


def test_orq_carrito_calcular_envia_lineas_al_endpoint():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["cuerpo"] = json.loads(solicitud.content)
        return httpx.Response(200, json=TOTALES)

    with crear_cliente(manejador) as cliente_api:
        datos = carrito.calcular(
            cliente_api,
            [{"producto_id": 1, "tipo_empaque": "caja", "cantidad": 2.0}],
        )

    assert datos["total"] == "26.75"
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/carrito/calcular"
    assert vistos["cuerpo"]["lineas"][0]["producto_id"] == 1


def test_orq_carrito_crear_pedido_envia_totales_del_backend():
    vistos = {}

    def manejador(solicitud):
        vistos["ruta"] = solicitud.url.path
        vistos["cuerpo"] = json.loads(solicitud.content)
        return httpx.Response(200, json={"id": 9, "estado": "pendiente"})

    pedido = carrito.construir_pedido(
        7,
        "Entrega en recepción",
        [{"producto_id": 1, "nombre": "Leche", "tipo_empaque": "caja", "cantidad": 2.0}],
        TOTALES,
    )

    with crear_cliente(manejador) as cliente_api:
        respuesta = carrito.crear_pedido(cliente_api, pedido)

    assert respuesta["id"] == 9
    assert vistos["ruta"] == "/api/v1/pedidos"
    assert vistos["cuerpo"]["total_estimado"] == "26.75"
    assert vistos["cuerpo"]["lineas"][0]["subtotal"] == "25.00"


@pytest.mark.anyio
async def test_orq_carrito_vacio_muestra_estado_y_enlace(monkeypatch):
    async with user_simulation(root=carrito.pagina_carrito) as user:
        await user.open("/")
        await user.should_see(CARRITO_VACIO)
        await user.should_see("Ver catálogo")


@pytest.mark.anyio
async def test_orq_carrito_con_lineas_muestra_totales_y_confirmacion(monkeypatch):
    monkeypatch.setattr(carrito, "calcular", lambda cliente, lines: TOTALES)

    async with user_simulation(root=carrito.pagina_carrito) as user:
        await user.open("/")
        with user.client:
            app.storage.tab["carrito"] = [
                {
                    "producto_id": 1,
                    "nombre": "Leche",
                    "tipo_empaque": "caja",
                    "cantidad": 2.0,
                    "precio_caja": "12.50",
                    "permite_media_caja": True,
                }
            ]
        await user.open("/")
        await user.should_see("Leche")
        await user.should_see("26.75")
        await user.should_see("Confirmar pedido")


@pytest.mark.anyio
async def test_orq_carrito_error_de_red_ofrece_reintento(monkeypatch):
    def sin_red(cliente_api, lineas):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr(carrito, "calcular", sin_red)

    async with user_simulation(root=carrito.pagina_carrito) as user:
        await user.open("/")
        with user.client:
            app.storage.tab["carrito"] = [
                {
                    "producto_id": 1,
                    "nombre": "Leche",
                    "tipo_empaque": "caja",
                    "cantidad": 2.0,
                }
            ]
        await user.open("/")
        await user.should_see(MENSAJE_CONEXION)
        await user.should_see("Reintentar")


@pytest.mark.anyio
async def test_orq_carrito_error_de_producto_explica_sin_codigos(monkeypatch):
    def producto_inactivo(cliente_api, lineas):
        raise ErrorApi(422, "El producto 'Leche' no está activo.", "VALIDATION_ERROR")

    monkeypatch.setattr(carrito, "calcular", producto_inactivo)

    async with user_simulation(root=carrito.pagina_carrito) as user:
        await user.open("/")
        with user.client:
            app.storage.tab["carrito"] = [
                {
                    "producto_id": 1,
                    "nombre": "Leche",
                    "tipo_empaque": "caja",
                    "cantidad": 2.0,
                }
            ]
        await user.open("/")
        await user.should_see("El producto 'Leche' no está activo.")
        await user.should_see("Revisa el producto indicado y vuelve a intentarlo.")
