from functools import lru_cache
from html import escape
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

SECCIONES = (
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

RUTA_SECCION = {
    ruta: seccion for seccion, enlaces in SECCIONES for _, ruta in enlaces
}
RUTA_SECCION.update(
    {
        "/facturacion/detalle": "Facturación",
        "/pedidos/detalle": "Pedidos",
        "/pedidos/convertir-a-factura": "Pedidos",
        "/pedidos/exitoso": "Pedidos",
    }
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


def _enlaces_moviles(activa: str) -> str:
    partes = []
    for seccion, enlaces in SECCIONES:
        for texto, ruta in enlaces:
            clases = "orq-cajon-enlace"
            if ruta == activa:
                clases += " orq-activo"
            partes.append(
                f'<a class="{clases}" href="{escape(ruta, quote=True)}">'
                f'<span>{escape(texto)}</span><small>{escape(seccion)}</small></a>'
            )
    return "".join(partes)


def _navegacion(activa: str) -> str:
    partes = []
    for seccion, enlaces in SECCIONES:
        en_seccion = RUTA_SECCION.get(activa) == seccion
        clases_boton = "orq-menu-boton"
        if en_seccion:
            clases_boton += " orq-activo"
        identificador = "orq-sub-" + seccion.lower().replace("ó", "o").replace(" ", "-")
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
            f"{escape(seccion)}<span class=\"orq-flecha\" aria-hidden=\"true\">⌄</span>"
            f"</button>"
            f'<div class="orq-submenu" id="{escape(identificador, quote=True)}" hidden>'
            f"{''.join(submenus)}</div></div>"
        )
    return "".join(partes)


def _cabecera(activa: str) -> str:
    negocio = datos_negocio().get("nombre", "")
    negocio_html = (
        f'<span class="orq-negocio">{escape(negocio)}</span>' if negocio else ""
    )
    return (
        f'<div class="orq-header-inner">'
        f'<a class="orq-marca" href="/" aria-label="Ir al inicio">'
        f'<span class="orq-petala">{MARCA}</span>'
        f'<span class="orq-nombre-marca">Orquídea</span>{negocio_html}</a>'
        f'<nav class="orq-nav-escritorio" aria-label="Secciones">'
        f"{_navegacion(activa)}</nav>"
        f'<div class="orq-header-acciones">'
        f'<a class="orq-boton orq-boton--primario orq-accion-emitir" '
        f'href="/facturacion/nueva">'
        f'<span class="orq-accion-completa">Emitir factura</span>'
        f'<span class="orq-accion-corta">Emitir</span></a>'
        f'<button type="button" class="orq-hamburguesa" aria-expanded="false" '
        f'aria-controls="orq-cajon" aria-label="Abrir menú">'
        f'<span aria-hidden="true">☰</span></button>'
        f"</div></div>"
        f'<nav class="orq-cajon" id="orq-cajon" hidden aria-label="Menú del negocio">'
        f"{_enlaces_moviles(activa)}</nav>"
    )


def montar_layout(
    titulo: str | None = None, *, ruta_activa: str = "", migas: str | None = None
) -> Any:
    """Encabezado fijo y, si aporta, un único título descriptivo de la página."""
    activa = ruta_activa or RUTA_SECCION.get(titulo or "", "/")
    ui.html(_cabecera(activa), sanitize=False, tag="header").classes(
        "orq-header orq-header-fijo w-full"
    )

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
