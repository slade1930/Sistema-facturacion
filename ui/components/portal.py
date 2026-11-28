"""Encabezado y navegación del portal de la empresa; etapa B."""

import asyncio
from html import escape

from nicegui import ui

from components.forms import boton_orquidea
from state import auth

SECCIONES = (
    (
        "Mi portal",
        (
            ("Inicio", "/portal/inicio"),
            ("Catálogo", "/portal/catalogo"),
            ("Carrito", "/portal/carrito"),
        ),
    ),
    (
        "Mis compras",
        (
            ("Pedidos", "/portal/pedidos"),
            ("Facturas", "/portal/facturas"),
            ("Mi cuenta", "/portal/mi-cuenta"),
        ),
    ),
)

RUTAS = {ruta for _, enlaces in SECCIONES for _, ruta in enlaces}


def _contador_carrito() -> str:
    return '<span class="orq-contador-carrito" data-orq-contador aria-label="Productos en el carrito"></span>'


def _enlaces_moviles(activa: str) -> str:
    partes = []
    for seccion, enlaces in SECCIONES:
        for texto, ruta in enlaces:
            clases = "orq-cajon-enlace"
            if ruta == activa:
                clases += " orq-activo"
            partes.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f"<span>{escape(texto)}"
                f"{_contador_carrito() if ruta == '/portal/carrito' else ''}</span>"
                f"<small>{escape(seccion)}</small></a>"
            )
    return "".join(partes)


def _navegacion(activa: str) -> str:
    partes = []
    for seccion, enlaces in SECCIONES:
        submenus = []
        for texto, ruta in enlaces:
            clases = "orq-subenlace"
            if ruta == activa:
                clases += " orq-activo"
            submenus.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f"{escape(texto)}"
                f"{_contador_carrito() if ruta == '/portal/carrito' else ''}</a>"
            )
        identificador = "orq-portal-" + seccion.lower().replace(" ", "-")
        partes.append(
            '<div class="orq-grupo">'
            '<button type="button" class="orq-menu-boton" aria-haspopup="true" '
            'aria-expanded="false" aria-controls="'
            + escape(identificador, quote=True)
            + '">'
            + escape(seccion)
            + '<span class="orq-flecha" aria-hidden="true">⌄</span></button>'
            '<div class="orq-submenu" id="'
            + escape(identificador, quote=True)
            + '" hidden>'
            + "".join(submenus)
            + "</div></div>"
        )
    return "".join(partes)


async def salir() -> None:
    api = auth.cliente_portal()
    try:
        await asyncio.to_thread(api.post, "/api/v1/auth/logout")
    except Exception:
        pass
    auth.cerrar_sesion()
    ui.navigate.to("/login")


def montar_portal(titulo: str, *, ruta_activa: str = "") -> None:
    """Cabecera propia del portal: nunca muestra menús de administración."""
    nombre = escape(auth.nombre_empresa())
    negocio = f'<span class="orq-negocio">{nombre}</span>' if nombre else ""
    cabecera = (
        '<div class="orq-header-inner">'
        '<a class="orq-marca" href="/portal/inicio" aria-label="Ir al inicio">'
        '<span class="orq-nombre-marca">Portal de empresas</span>'
        f"{negocio}</a>"
        '<nav class="orq-nav-escritorio" aria-label="Secciones del portal">'
        + _navegacion(ruta_activa if ruta_activa in RUTAS else "/portal/inicio")
        + "</nav>"
        '<button type="button" class="orq-hamburguesa" aria-expanded="false" '
        'aria-controls="orq-cajon" aria-label="Abrir menú">'
        '<span aria-hidden="true">☰</span></button>'
        "</div>"
        '<nav class="orq-cajon" id="orq-cajon" hidden aria-label="Menú del portal">'
        + _enlaces_moviles(ruta_activa if ruta_activa in RUTAS else "/portal/inicio")
        + "</nav>"
    )
    ui.html(cabecera, sanitize=False, tag="header").classes(
        "orq-header orq-header-fijo w-full"
    )

    with ui.row().classes("orq-barra-acciones w-full"):
        if nombre:
            ui.label(f"Empresa: {nombre}").classes("orq-bloque-ayuda")
        boton_orquidea("Salir", salir, variante="texto")

    with ui.element("section").classes("orq-encabezado-pagina w-full"):
        ui.label(titulo).classes("orq-titulo")


__all__ = ["SECCIONES", "montar_portal", "salir"]
