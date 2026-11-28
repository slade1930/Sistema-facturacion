"""Sesión del portal en la interfaz. Empresa y admin; etapa B.

El token viaja en las cabeceras de `ClienteApi`. La interfaz nunca decide
qué puede ver: el backend filtra todo con ese token. Acá solo guardamos la
sesión de la pestaña y mostramos lo que el backend devuelve.
"""

from typing import Any

from nicegui import app, ui

from state.cliente_api import ClienteApi

CLAVE_TOKEN = "portal_token"
CLAVE_USUARIO = "portal_usuario"
CLAVE_COMPRA = "portal_clave_compra"

SECTORES = {
    "tecnologia": "Tecnología",
    "turismo": "Turismo",
    "supermercado": "Supermercado",
}


async def conectar() -> None:
    """Habilita el almacenamiento de la pestaña antes de leer la sesión."""
    await ui.context.client.connected()


def _almacen() -> Any:
    """Almacenamiento de la pestaña; fuera de la interfaz no hay sesión."""
    try:
        return app.storage.tab
    except Exception:
        return None


def token() -> str | None:
    almacen = _almacen()
    if almacen is None:
        return None
    valor = almacen.get(CLAVE_TOKEN)
    return str(valor) if valor else None


def datos_usuario() -> dict[str, Any]:
    almacen = _almacen()
    if almacen is None:
        return {}
    datos = almacen.get(CLAVE_USUARIO)
    return dict(datos) if isinstance(datos, dict) else {}


def guardar_sesion(respuesta: dict[str, Any]) -> None:
    """Guarda el token y el resumen; cambiar de cuenta vacía el carrito."""
    almacen = _almacen()
    if almacen is None:
        return
    empresa = respuesta.get("empresa") or {}
    anterior = datos_usuario()
    anterior_id = anterior.get("cuenta_id")
    nuevo_id = respuesta.get("cuenta_id")
    anterior_nombre = str((anterior.get("empresa") or {}).get("nombre") or "").strip()
    nuevo_nombre = str(empresa.get("nombre") or "").strip()
    cambio = not anterior or anterior_id != nuevo_id or anterior_nombre != nuevo_nombre
    if cambio:
        for clave in ("carrito", CLAVE_COMPRA):
            almacen.pop(clave, None)
    almacen[CLAVE_TOKEN] = respuesta.get("token")
    almacen[CLAVE_USUARIO] = {
        "rol": respuesta.get("rol"),
        "cuenta_id": nuevo_id,
        "empresa": dict(empresa) if isinstance(empresa, dict) else {},
        "debe_cambiar_clave": bool(respuesta.get("debe_cambiar_clave")),
    }


def cerrar_sesion() -> None:
    almacen = _almacen()
    if almacen is None:
        return
    for clave in (CLAVE_TOKEN, CLAVE_USUARIO, CLAVE_COMPRA, "carrito"):
        almacen.pop(clave, None)


def es_empresa() -> bool:
    return datos_usuario().get("rol") == "empresa"


def nombre_empresa() -> str:
    empresa = datos_usuario().get("empresa") or {}
    return str(empresa.get("nombre") or "").strip()


def cliente_portal() -> ClienteApi:
    """Cliente con la API-Key del despliegue y el token de la pestaña."""
    return ClienteApi(token=token())


def exigir_sesion() -> bool:
    """Muestra el acceso si no hay sesión y devuelve si puede seguir."""
    if token():
        return True
    with ui.element("section").classes("orq-bloque w-full"):
        ui.label("Inicia sesión para entrar al portal.").classes("orq-titulo")
        ui.label("Tu empresa, tus compras y tus facturas en un solo lugar.").classes(
            "orq-bloque-ayuda"
        )
        ui.link("Ir a iniciar sesión", "/login").classes(
            "orq-boton orq-boton--primario"
        )
    return False


__all__ = [
    "CLAVE_COMPRA",
    "SECTORES",
    "cliente_portal",
    "cerrar_sesion",
    "conectar",
    "datos_usuario",
    "es_empresa",
    "exigir_sesion",
    "guardar_sesion",
    "nombre_empresa",
    "token",
]
