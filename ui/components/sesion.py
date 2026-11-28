"""Encabezado compartido: la misma marca para todas las cuentas, sin mezclar menús."""

from hashlib import md5
from html import escape
from pathlib import Path
from typing import Any

from nicegui import ui

MARCA = """
<svg viewBox="0 0 48 48" role="img" aria-label="Orquídea">
  <path d="M24 42C24 31 14 27 10 19 6 11 13 5 24 13 35 5 42 11 38 19 34 27 24 31 24 42Z"
        fill="none" stroke="#220A3A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M24 42V20m0 8-9-6m9 6 9-6" fill="none" stroke="#D4157F" stroke-width="2" stroke-linecap="round"/>
</svg>
"""


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


def cabecera_publica() -> None:
    """Cabecera de acceso sin nav de negocio: no hay sesión todavía."""
    cabecera = (
        '<div class="orq-header-inner">'
        f"{marca()}</div>"
    )
    ui.html(cabecera, sanitize=False).classes(
        "orq-header orq-header-fijo w-full"
    )


CSS_HEADER = Path(__file__).resolve().parents[1] / "static" / "orquidea.css"
VERSION = md5(CSS_HEADER.read_bytes()).hexdigest()[:8] if CSS_HEADER.exists() else ""
ui.add_head_html(
    f'<link rel="stylesheet" href="/static/orquidea.css?v={VERSION}">',
    shared=True,
)


__all__ = ["cabecera_publica", "destino_sesion", "marca", "petalo"]
