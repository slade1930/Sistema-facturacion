"""Encabezado y navegación del administrador; etapa C2.

Reutiliza las clases ORQUIDEA del menú superior y carga solo el CSS propio
de administración desde este módulo.
"""

from hashlib import md5
from html import escape
from pathlib import Path
from typing import Any

from nicegui import ui

SECCIONES_ADMIN = (
    ("Panel", (("Panel", "/admin/panel"),)),
    (
        "Facturación",
        (
            ("Emitir factura", "/facturacion/nueva"),
            ("Historial", "/facturacion/historial"),
        ),
    ),
    (
        "Catálogo",
        (
            ("Productos", "/admin/catalogo"),
            ("Categorías", "/admin/catalogo/categorias"),
        ),
    ),
    ("Inventario", (("Inventario", "/admin/inventario"),)),
    (
        "Pedidos",
        (
            ("Por facturar", "/admin/pedidos/por-facturar"),
            ("Todos", "/admin/pedidos"),
        ),
    ),
    ("Empresas", (("Empresas", "/admin/empresas"),)),
    (
        "Consultar",
        (
            ("Verificar factura", "/verificar"),
            ("Auditoría", "/admin/auditoria"),
        ),
    ),
    ("Negocio", (("Configuración", "/configuracion"),)),
)

GRUPOS_ADMIN = frozenset(
    {"Facturación", "Catálogo", "Pedidos", "Consultar", "Negocio"}
)
RUTAS_ADMIN = {ruta for _, enlaces in SECCIONES_ADMIN for _, ruta in enlaces} | {
    "/admin"
}

CSS = Path(__file__).resolve().parents[2] / "static" / "orquidea-admin.css"
VERSION = md5(CSS.read_bytes()).hexdigest()[:8] if CSS.exists() else "sin-version"
ui.add_head_html(
    f'<link rel="stylesheet" href="/static/orquidea-admin.css?v={VERSION}">',
    shared=True,
)


def _activa(ruta_activa: str) -> str:
    if ruta_activa in RUTAS_ADMIN:
        return "/admin/panel" if ruta_activa == "/admin" else ruta_activa
    return "/admin/panel"


def _enlaces_moviles(activa: str) -> str:
    partes = []
    for seccion, enlaces in SECCIONES_ADMIN:
        for texto, ruta in enlaces:
            clases = "orq-cajon-enlace"
            if ruta == activa:
                clases += " orq-activo"
            partes.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f"<span>{escape(texto)}</span><small>{escape(seccion)}</small></a>"
            )
    return "".join(partes)


def _navegacion(activa: str) -> str:
    partes = []
    for seccion, enlaces in SECCIONES_ADMIN:
        en_seccion = any(ruta == activa for _, ruta in enlaces)
        if seccion not in GRUPOS_ADMIN:
            texto, ruta = enlaces[0]
            clases = "orq-menu-boton orq-admin-enlace"
            if ruta == activa:
                clases += " orq-activo"
            partes.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}" '
                f'aria-current="{"page" if ruta == activa else "false"}">'
                f"{escape(texto)}</a>"
            )
            continue

        clases_boton = "orq-menu-boton"
        if en_seccion:
            clases_boton += " orq-activo"
        identificador = "orq-admin-" + seccion.lower().replace("ó", "o").replace(
            " ", "-"
        )
        submenus = []
        for texto, ruta in enlaces:
            clases = "orq-subenlace"
            if ruta == activa:
                clases += " orq-activo"
            submenus.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f"{escape(texto)}</a>"
            )
        partes.append(
            f'<div class="orq-grupo">'
            f'<button type="button" class="{clases_boton}" aria-haspopup="true" '
            f'aria-expanded="false" aria-controls="{escape(identificador, quote=True)}">'
            f"{escape(seccion)}"
            f'<span class="orq-flecha" aria-hidden="true">⌄</span></button>'
            f'<div class="orq-submenu" id="{escape(identificador, quote=True)}" hidden>'
            f"{''.join(submenus)}</div></div>"
        )
    return "".join(partes)


def montar_admin(titulo: str, *, ruta_activa: str = "") -> Any:
    """Cabecera propia del administrador con un único título de página."""
    activa = _activa(ruta_activa)
    cabecera = (
        '<div class="orq-header-inner">'
        '<a class="orq-marca" href="/admin/panel" aria-label="Ir al panel">'
        '<span class="orq-nombre-marca">Orquídea · Administración</span></a>'
        '<nav class="orq-nav-escritorio" aria-label="Secciones del administrador">'
        + _navegacion(activa)
        + "</nav>"
        '<button type="button" class="orq-hamburguesa" aria-expanded="false" '
        'aria-controls="orq-cajon" aria-label="Abrir menú">'
        '<span aria-hidden="true">☰</span></button>'
        "</div>"
        '<nav class="orq-cajon" id="orq-cajon" hidden aria-label="Menú del administrador">'
        + _enlaces_moviles(activa)
        + "</nav>"
    )
    ui.html(cabecera, sanitize=False, tag="header").classes(
        "orq-header orq-header-fijo orq-admin w-full"
    )
    with ui.element("section").classes("orq-encabezado-pagina w-full"):
        ui.label(titulo).classes("orq-titulo")


__all__ = ["GRUPOS_ADMIN", "RUTAS_ADMIN", "SECCIONES_ADMIN", "montar_admin"]
