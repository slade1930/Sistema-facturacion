import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.facturacion.configuracion import (
    actualizar_configuracion,
    construir_cambios,
    obtener_configuracion,
    subir_logo,
)
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_obtener_configuracion_envia_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(
            200,
            json={"id": 1, "empresa_nombre": "Acme", "logo": None},
        )

    with crear_cliente(manejador) as cliente_api:
        datos = obtener_configuracion(cliente_api)

    assert datos["empresa_nombre"] == "Acme"
    assert vistos["metodo"] == "GET"
    assert vistos["ruta"] == "/api/v1/configuracion"
    assert vistos["api_key"] == "clave-de-prueba"


def test_obtener_configuracion_inexistente_es_404():
    def manejador(solicitud):
        return httpx.Response(
            404,
            json={
                "detail": "La configuración del negocio no existe.",
                "code": "NOT_FOUND",
            },
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            obtener_configuracion(cliente_api)
        except ErrorApi as error:
            assert error.status_code == 404
            assert error.code == "NOT_FOUND"
            assert error.detail == "La configuración del negocio no existe."
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_construir_cambios_solo_envia_campos_editables():
    valores = {
        "empresa_nombre": "  Acme  ",
        "empresa_ruc": "123",
        "mostrar_ruc": True,
        "empresa_direccion": "   ",
        "empresa_correo": "correo@acme.com",
        "empresa_telefono": None,
        "color_principal": "#3A0088",
        "color_barra_factura": "#5B3A9E",
        "color_tabla": "#3A0088",
        "datos_bancarios": "",
        "notas_predeterminadas": "Gracias",
        "id": 1,
        "actualizado": "2026-01-01",
        "logo": "media/viejo.png",
    }

    cambios = construir_cambios(valores)

    assert "id" not in cambios
    assert "actualizado" not in cambios
    assert "logo" not in cambios
    assert cambios["empresa_nombre"] == "Acme"
    assert cambios["empresa_direccion"] is None
    assert cambios["datos_bancarios"] is None
    assert cambios["mostrar_ruc"] is True


def test_actualizar_configuracion_envia_put_y_cuerpo():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["cuerpo"] = solicitud.read()
        return httpx.Response(200, json={"id": 1, "empresa_nombre": "Acme"})

    cambios = construir_cambios({"empresa_nombre": " Acme ", "mostrar_ruc": False})

    with crear_cliente(manejador) as cliente_api:
        datos = actualizar_configuracion(cliente_api, cambios)

    assert datos["empresa_nombre"] == "Acme"
    assert vistos["metodo"] == "PUT"
    assert vistos["ruta"] == "/api/v1/configuracion"
    assert b'"empresa_nombre":"Acme"' in vistos["cuerpo"]
    assert b'"empresa_direccion":null' in vistos["cuerpo"]


def test_actualizar_configuracion_muestra_errores_de_validacion():
    def manejador(solicitud):
        return httpx.Response(
            422,
            json={
                "detail": "Datos inválidos.",
                "code": "VALIDATION_ERROR",
                "errors": [{"campo": "empresa_ruc", "mensaje": "Requerido"}],
            },
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            actualizar_configuracion(cliente_api, {})
        except ErrorApi as error:
            assert error.status_code == 422
            assert error.code == "VALIDATION_ERROR"
            assert error.errors == [
                {"campo": "empresa_ruc", "mensaje": "Requerido"}
            ]
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_subir_logo_envia_multipart():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        vistos["cuerpo"] = solicitud.content
        return httpx.Response(200, json={"id": 1, "logo": "media/nuevo.png"})

    contenido = b"\x89PNG\r\n\x1a\ndatos"

    with crear_cliente(manejador) as cliente_api:
        datos = subir_logo(cliente_api, "logo.png", contenido, "image/png")

    assert datos["logo"] == "media/nuevo.png"
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/configuracion/logo"
    assert vistos["api_key"] == "clave-de-prueba"
    assert b'name="archivo"' in vistos["cuerpo"]
    assert b'filename="logo.png"' in vistos["cuerpo"]
    assert contenido in vistos["cuerpo"]


def test_subir_logo_formato_invalido_es_422():
    def manejador(solicitud):
        return httpx.Response(
            422,
            json={
                "detail": "Formato no permitido. Use PNG, JPG o WEBP.",
                "code": "VALIDATION_ERROR",
            },
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            subir_logo(cliente_api, "logo.gif", b"GIF", "image/gif")
        except ErrorApi as error:
            assert error.status_code == 422
            assert error.code == "VALIDATION_ERROR"
        else:
            raise AssertionError("Se esperaba ErrorApi")
