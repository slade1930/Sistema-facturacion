from html import escape
from typing import Any

from nicegui import ui

from components.sesion import (
    ACCION_EMITIR,
    ACCION_PEDIDO,
    DIRECTAS_ADMIN,
    RUTA_SECCION_NEGOCIO,
    SECCIONES_ADMIN,
    SECCIONES_NEGOCIO,
    SECCIONES_PORTAL,
    cabecera_html,
    datos_negocio,
    nombre_negocio,
    rol_actual,
)

SECCIONES = None  # se resuelve por rol en cada render
RUTA_SECCION = RUTA_SECCION_NEGOCIO


def montar_layout(
    titulo: str | None = None, *, ruta_activa: str = "", migas: str | None = None
) -> Any:
    """Cabecera ORQUÍDEA única: cambian los enlaces, no el diseño ni el rol."""
    rol = rol_actual()
    if rol == "admin":
        secciones = SECCIONES_ADMIN
        directas = DIRECTAS_ADMIN
        prefijo = "orq-admin"
        clases = "orq-header orq-header-fijo orq-admin w-full"
        aria_cajon = "Menú del administrador"
        href = "/admin/panel"
        etiqueta = "Ir al panel"
        aria_nav = "Secciones del administrador"
        accion = ACCION_EMITIR
        contador = ()
    elif rol == "empresa":
        secciones = SECCIONES_PORTAL
        directas = ()
        prefijo = "orq-portal"
        clases = "orq-header orq-header-fijo w-full"
        aria_cajon = "Menú del portal"
        href = "/portal/inicio"
        etiqueta = "Ir al inicio"
        aria_nav = "Secciones del portal"
        accion = ACCION_PEDIDO
        contador = ("/portal/carrito",)
    else:
        secciones = SECCIONES_NEGOCIO
        directas = ()
        prefijo = "orq-seccion"
        clases = "orq-header orq-header-fijo w-full"
        aria_cajon = "Menú"
        href = "/"
        etiqueta = "Ir al inicio"
        aria_nav = "Secciones"
        accion = ACCION_EMITIR
        contador = ("/carrito",)

    activa = ruta_activa or RUTA_SECCION_NEGOCIO.get(titulo or "", "/")
    if not any(ruta == activa for _, enlaces in secciones for _, ruta in enlaces):
        activa = "/admin/panel" if rol == "admin" else "/"

    ui.html(
        cabecera_html(
            secciones,
            activa,
            href=href,
            etiqueta=etiqueta,
            nombre=nombre_negocio(),
            aria_nav=aria_nav,
            aria_cajon=aria_cajon,
            accion=accion,
            directas=directas,
            contador=contador,
            prefijo=prefijo,
        ),
        sanitize=False,
    ).classes(clases)

    if titulo is None:
        return None

    with ui.element("section").classes("orq-encabezado-pagina w-full") as cabecera:
        if migas:
            ui.html(
                f'<span class="orq-migas">{escape(migas)}</span>', sanitize=False
            )
        ui.label(titulo).classes("orq-titulo")
    return cabecera


__all__ = [
    "SECCIONES",
    "RUTA_SECCION",
    "datos_negocio",
    "montar_layout",
    "nombre_negocio",
]
