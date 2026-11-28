"""Cabecera única ORQUÍDEA: mismo diseño para todas las cuentas, menús por rol."""

from functools import lru_cache
from hashlib import md5
from html import escape
from pathlib import Path
from typing import Any

from nicegui import ui

from state.cliente_api import ClienteApi

MARCA = """
<svg viewBox="0 0 48 48" role="img" aria-label="Orquídea">
  <path d="M24 42C24 31 14 27 10 19 6 11 13 5 24 13 35 5 42 11 38 19 34 27 24 31 24 42Z"
        fill="none" stroke="#220A3A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M24 42V20m0 8-9-6m9 6 9-6" fill="none" stroke="#D4157F" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

SECCIONES_NEGOCIO = (
    (
        "Facturación",
        (
            ("Talonario", "/facturacion/nueva"),
            ("Emitidas", "/facturacion/historial"),
        ),
    ),
    (
        "Catálogo",
        (
            ("Productos", "/catalogo"),
            ("Carrito", "/carrito"),
        ),
    ),
    (
        "Pedidos",
        (
            ("Por facturar", "/pedidos/por-facturar"),
            ("Nuevo pedido", "/pedidos/formulario"),
        ),
    ),
    (
        "Consultar",
        (("Verificación", "/verificar"),),
    ),
    (
        "Negocio",
        (("Datos del negocio", "/configuracion"),),
    ),
)

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

SECCIONES_PORTAL = (
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

GRUPOS_ADMIN = frozenset(
    {"Facturación", "Catálogo", "Pedidos", "Consultar", "Negocio"}
)
DIRECTAS_ADMIN = frozenset(
    seccion for seccion, _ in SECCIONES_ADMIN if seccion not in GRUPOS_ADMIN
)
RUTAS_ADMIN = {ruta for _, enlaces in SECCIONES_ADMIN for _, ruta in enlaces} | {
    "/admin"
}
RUTAS_PORTAL = {ruta for _, enlaces in SECCIONES_PORTAL for _, ruta in enlaces}

RUTA_SECCION_NEGOCIO = {
    ruta: seccion for seccion, enlaces in SECCIONES_NEGOCIO for _, ruta in enlaces
}
RUTA_SECCION_NEGOCIO.update(
    {
        "/facturacion/detalle": "Facturación",
        "/pedidos/detalle": "Pedidos",
        "/pedidos/convertir-a-factura": "Pedidos",
        "/pedidos/exitoso": "Pedidos",
    }
)

ACCION_EMITIR = (
    '<a class="orq-boton orq-boton--primario orq-accion-emitir" '
    'href="/facturacion/nueva">'
    '<span class="orq-accion-completa">Emitir factura</span>'
    '<span class="orq-accion-corta">Emitir</span></a>'
)
ACCION_PEDIDO = (
    '<a class="orq-boton orq-boton--primario orq-accion-emitir" '
    'href="/portal/catalogo">'
    '<span class="orq-accion-completa">Hacer pedido</span>'
    '<span class="orq-accion-corta">Pedir</span></a>'
)


@lru_cache(maxsize=1)
def datos_negocio() -> dict[str, str]:
    """Nombre y RUC guardados, sin exponer rutas ni datos técnicos."""
    try:
        datos = ClienteApi(timeout=2).get("/api/v1/configuracion")
    except Exception:
        return {}
    if not isinstance(datos, dict):
        return {}
    return {
        "nombre": str(datos.get("empresa_nombre") or "").strip(),
        "ruc": str(datos.get("empresa_ruc") or "").strip(),
    }


def nombre_negocio() -> str:
    return datos_negocio().get("nombre", "")


def rol_actual() -> str:
    """Rol de la pestaña; falla en silencio durante el primer render."""
    try:
        from state import auth

        return str(auth.datos_usuario().get("rol") or "")
    except Exception:
        return ""


def secciones_activas() -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """Cada cuenta ve su menú, pero todos usan la misma cabecera."""
    if rol_actual() == "admin":
        return SECCIONES_ADMIN
    if rol_actual() == "empresa":
        return SECCIONES_PORTAL
    return SECCIONES_NEGOCIO


def ruta_seccion(secciones: Any, activa: str) -> str:
    for seccion, enlaces in secciones:
        if any(ruta == activa for _, ruta in enlaces):
            return seccion
    return ""


def petalo() -> str:
    """El logotipo de siempre, sin depender de los datos del negocio."""
    return f'<span class="orq-petala">{MARCA}</span>'


def marca(href: str = "/", etiqueta: str = "Ir al inicio", nombre: str = "") -> str:
    """Bloque de marca con el petalo, el nombre y, si aporta, la cuenta activa."""
    negocio = (
        f'<span class="orq-negocio">{escape(nombre)}</span>' if nombre.strip() else ""
    )
    return (
        f'<a class="orq-marca" href="{escape(href, quote=True)}" '
        f'aria-label="{escape(etiqueta, quote=True)}">'
        f"{petalo()}"
        '<span class="orq-nombre-marca">Orquídea</span>'
        f"{negocio}</a>"
    )


def destino_sesion(respuesta: dict[str, Any]) -> str:
    """La cuenta admin entra al panel; la empresa, a su portal."""
    if respuesta.get("debe_cambiar_clave"):
        return "/portal/cambiar-clave"
    return "/admin/panel" if respuesta.get("rol") == "admin" else "/portal/inicio"


def _contador_carrito() -> str:
    return '<span class="orq-contador-carrito" data-orq-contador aria-label="Productos en el carrito"></span>'


def _identificador(prefijo: str, seccion: str) -> str:
    return prefijo + "-" + seccion.lower().replace("ó", "o").replace(" ", "-")


def navegacion_html(
    secciones: Any,
    activa: str,
    *,
    prefijo: str,
    directas: Any = (),
    contador: Any = (),
) -> str:
    partes = []
    for seccion, enlaces in secciones:
        if seccion in directas:
            texto, ruta = enlaces[0]
            es_activa = ruta == activa
            clases = "orq-menu-boton orq-admin-enlace"
            if es_activa:
                clases += " orq-activo"
            partes.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}" '
                f'aria-current="{"page" if es_activa else "false"}">'
                f"{escape(texto)}</a>"
            )
            continue

        clases_boton = "orq-menu-boton"
        if ruta_seccion(((seccion, enlaces),), activa):
            clases_boton += " orq-activo"
        identificador = _identificador(prefijo, seccion)
        submenus = []
        for texto, ruta in enlaces:
            clases = "orq-subenlace"
            if ruta == activa:
                clases += " orq-activo"
            extra = _contador_carrito() if ruta in contador else ""
            submenus.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f"{escape(texto)}{extra}</a>"
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


def enlaces_moviles_html(
    secciones: Any, activa: str, *, contador: Any = ()
) -> str:
    partes = []
    for seccion, enlaces in secciones:
        for texto, ruta in enlaces:
            clases = "orq-cajon-enlace"
            if ruta == activa:
                clases += " orq-activo"
            extra = _contador_carrito() if ruta in contador else ""
            partes.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f"<span>{escape(texto)}{extra}</span>"
                f"<small>{escape(seccion)}</small></a>"
            )
    return "".join(partes)


def cabecera_html(
    secciones: Any,
    activa: str,
    *,
    href: str,
    etiqueta: str,
    nombre: str = "",
    aria_nav: str = "Secciones",
    aria_cajon: str = "Menú",
    accion: str = "",
    directas: Any = (),
    contador: Any = (),
    prefijo: str = "orq-seccion",
) -> str:
    """Un solo encabezado: cambian los enlaces, no el diseño."""
    return (
        '<div class="orq-header-inner">'
        + marca(href, etiqueta, nombre)
        + f'<nav class="orq-nav-escritorio" aria-label="{escape(aria_nav, quote=True)}">'
        + navegacion_html(
            secciones, activa, prefijo=prefijo, directas=directas, contador=contador
        )
        + "</nav>"
        '<div class="orq-header-acciones">'
        + accion
        + '<button type="button" class="orq-hamburguesa" aria-expanded="false" '
        'aria-controls="orq-cajon" aria-label="Abrir menú">'
        '<span aria-hidden="true">☰</span></button>'
        "</div></div>"
        f'<nav class="orq-cajon" id="orq-cajon" hidden aria-label="{escape(aria_cajon, quote=True)}">'
        + enlaces_moviles_html(secciones, activa, contador=contador)
        + "</nav>"
    )


def cabecera_publica() -> None:
    """Cabecera de acceso sin nav de negocio: no hay sesión todavía."""
    ui.html(
        '<div class="orq-header-inner">' f"{marca()}</div>", sanitize=False
    ).classes("orq-header orq-header-fijo w-full")


CSS_HEADER = Path(__file__).resolve().parents[1] / "static" / "orquidea.css"
VERSION = md5(CSS_HEADER.read_bytes()).hexdigest()[:8] if CSS_HEADER.exists() else ""
ui.add_head_html(
    f'<link rel="stylesheet" href="/static/orquidea.css?v={VERSION}">',
    shared=True,
)


__all__ = [
    "ACCION_EMITIR",
    "ACCION_PEDIDO",
    "DIRECTAS_ADMIN",
    "GRUPOS_ADMIN",
    "RUTA_SECCION_NEGOCIO",
    "RUTAS_ADMIN",
    "RUTAS_PORTAL",
    "SECCIONES_ADMIN",
    "SECCIONES_NEGOCIO",
    "SECCIONES_PORTAL",
    "cabecera_html",
    "cabecera_publica",
    "datos_negocio",
    "destino_sesion",
    "enlaces_moviles_html",
    "marca",
    "navegacion_html",
    "nombre_negocio",
    "petalo",
    "rol_actual",
    "ruta_seccion",
    "secciones_activas",
]
