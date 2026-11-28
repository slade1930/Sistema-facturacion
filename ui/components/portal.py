"""Portal de la empresa sobre la cabecera ORQUÍDEA compartida; etapa B."""

import asyncio

from nicegui import ui

from components.forms import boton_orquidea
from components.sesion import (
    ACCION_PEDIDO,
    RUTAS_PORTAL,
    SECCIONES_PORTAL,
    cabecera_html,
    enlaces_moviles_html,
    navegacion_html,
)
from state import auth

SECCIONES = SECCIONES_PORTAL
RUTAS = RUTAS_PORTAL
CONTADOR = ("/portal/carrito",)


def _navegacion(activa: str) -> str:
    return navegacion_html(
        SECCIONES, activa, prefijo="orq-portal", contador=CONTADOR
    )


def _enlaces_moviles(activa: str) -> str:
    return enlaces_moviles_html(SECCIONES, activa, contador=CONTADOR)


async def salir() -> None:
    api = auth.cliente_portal()
    try:
        await asyncio.to_thread(api.post, "/api/v1/auth/logout")
    except Exception:
        pass
    auth.cerrar_sesion()
    ui.navigate.to("/login")


def montar_portal(titulo: str, *, ruta_activa: str = "") -> None:
    """Misma cabecera que el administrador, con solo las secciones de la empresa."""
    nombre = auth.nombre_empresa()
    activa = ruta_activa if ruta_activa in RUTAS else "/portal/inicio"
    ui.html(
        cabecera_html(
            SECCIONES,
            activa,
            href="/portal/inicio",
            etiqueta="Ir al inicio",
            nombre=nombre,
            aria_nav="Secciones del portal",
            aria_cajon="Menú del portal",
            accion=ACCION_PEDIDO,
            contador=CONTADOR,
            prefijo="orq-portal",
        ),
        sanitize=False,
    ).classes("orq-header orq-header-fijo w-full")

    with ui.row().classes("orq-barra-acciones w-full"):
        if nombre:
            ui.label(f"Empresa: {nombre}").classes("orq-bloque-ayuda")
        boton_orquidea("Salir", salir, variante="texto")

    with ui.element("section").classes("orq-encabezado-pagina w-full"):
        ui.label(titulo).classes("orq-titulo")


__all__ = ["SECCIONES", "montar_portal", "salir"]
