import json
import sys
from pathlib import Path

import httpx
import pytest
from nicegui import ui
from nicegui.testing import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.facturacion import configuracion
from state.cliente_api import ClienteApi, ErrorApi


MENSAJE_CONEXION = (
    "No pudimos conectar con el sistema. Revisa tu conexión e inténtalo de nuevo."
)


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def escribir_campo(user, etiqueta: str, valor: str) -> None:
    elemento = next(
        elemento
        for elemento in user.find(ui.input).elements
        if elemento.props.get("label") == etiqueta
    )
    with user.client:
        elemento.value = valor
        elemento.update()


def test_orq_config_solo_envia_campos_modificados():
    actual = {
        "empresa_nombre": "Taller Orquídea",
        "empresa_ruc": "RUC-1",
        "empresa_direccion": "Calle 1",
        "mostrar_ruc": True,
    }
    valores = dict(actual)
    valores["empresa_direccion"] = "Calle 2"

    cambios = configuracion.cambios_para_guardar(actual, valores)

    assert cambios == {"empresa_direccion": "Calle 2"}


def test_orq_config_primera_carga_envia_nombre_y_ruc():
    valores = {
        "empresa_nombre": "Taller Orquídea",
        "empresa_ruc": "RUC-1",
        "empresa_direccion": "   ",
        "mostrar_ruc": False,
    }

    cambios = configuracion.cambios_para_guardar({}, valores, inicial=True)

    assert cambios["empresa_nombre"] == "Taller Orquídea"
    assert cambios["empresa_ruc"] == "RUC-1"
    assert cambios["empresa_direccion"] is None
    assert cambios["mostrar_ruc"] is False


def test_orq_config_sube_logo_con_la_llave_de_la_api():
    vistos = {}

    def manejador(solicitud):
        vistos["metodo"] = solicitud.method
        vistos["ruta"] = solicitud.url.path
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        vistos["cuerpo"] = solicitud.content
        return httpx.Response(200, json={"logo": "/media/logo.png"})

    with crear_cliente(manejador) as cliente_api:
        respuesta = configuracion.subir_logo(
            cliente_api, "logo.png", b"contenido", "image/png"
        )

    assert respuesta == {"logo": "/media/logo.png"}
    assert vistos["metodo"] == "POST"
    assert vistos["ruta"] == "/api/v1/configuracion/logo"
    assert vistos["api_key"] == "clave-de-prueba"
    assert b"logo.png" in vistos["cuerpo"]


def test_orq_config_url_del_logo_no_acepta_rutas_ajenas():
    assert configuracion._url_logo("/media/logo.png") == "/media/logo.png"
    assert configuracion._url_logo("../secreto.png") is None
    assert configuracion._url_logo("https://ejemplo.com/logo.png") is None


@pytest.mark.anyio
async def test_orq_config_sin_fila_muestra_formulario_de_primera_vez(monkeypatch):
    def sin_fila(cliente_api):
        raise ErrorApi(404, "La configuración del negocio no existe.", "NOT_FOUND")

    monkeypatch.setattr(configuracion, "obtener_configuracion", sin_fila)
    monkeypatch.setattr(configuracion, "_recomendaciones_pendientes", lambda cliente: False)

    async with user_simulation(root=configuracion.pagina_configuracion) as user:
        await user.open("/")
        await user.should_see("Aún no configuraste tu negocio.")
        await user.should_see("Empresa")
        await user.should_see("RUC")
        await user.should_not_see("No se pudieron cargar los datos del negocio.")


@pytest.mark.anyio
async def test_orq_config_guardado_muestra_aviso_y_envia_cambios(monkeypatch):
    actual = {"empresa_nombre": "Taller Orquídea", "empresa_ruc": "RUC-1"}
    enviado = {}

    def guardar(cliente_api, cambios):
        enviado.update(cambios)
        return {**actual, **cambios}

    monkeypatch.setattr(configuracion, "obtener_configuracion", lambda cliente: actual)
    monkeypatch.setattr(configuracion, "actualizar_configuracion", guardar)
    monkeypatch.setattr(configuracion, "_recomendaciones_pendientes", lambda cliente: False)

    async with user_simulation(root=configuracion.pagina_configuracion) as user:
        await user.open("/")
        await user.should_see("Taller Orquídea")
        escribir_campo(user, "Dirección", "Calle 2")
        user.find(kind=ui.button, content="Guardar").click()
        await user.should_see("Cambios guardados")

    assert enviado["empresa_direccion"] == "Calle 2"
    assert "empresa_nombre" not in enviado


@pytest.mark.anyio
async def test_orq_config_error_de_red_muestra_mensaje_y_reintento(monkeypatch):
    def sin_red(cliente_api):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr(configuracion, "obtener_configuracion", sin_red)

    async with user_simulation(root=configuracion.pagina_configuracion) as user:
        await user.open("/")
        await user.should_see(MENSAJE_CONEXION)
        await user.should_see("Reintentar")


@pytest.mark.anyio
async def test_orq_config_error_de_campo_aparece_bajo_el_campo(monkeypatch):
    actual = {"empresa_nombre": "Taller Orquídea", "empresa_ruc": "RUC-1"}

    def rechazar(cliente_api, cambios):
        raise ErrorApi(
            422,
            "Datos inválidos.",
            "VALIDATION_ERROR",
            [{"loc": ["body", "empresa_ruc"], "msg": "Field required"}],
        )

    monkeypatch.setattr(configuracion, "obtener_configuracion", lambda cliente: actual)
    monkeypatch.setattr(configuracion, "actualizar_configuracion", rechazar)
    monkeypatch.setattr(configuracion, "_recomendaciones_pendientes", lambda cliente: False)

    async with user_simulation(root=configuracion.pagina_configuracion) as user:
        await user.open("/")
        escribir_campo(user, "RUC", "")
        user.find(kind=ui.button, content="Guardar").click()
        await user.should_see("RUC: falta este dato.")
