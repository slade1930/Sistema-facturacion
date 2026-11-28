"""Menú del administrador sobre la cabecera ORQUÍDEA compartida; etapa C2."""

from hashlib import md5
from pathlib import Path
from typing import Any

from nicegui import ui

from components.sesion import (
    ACCION_EMITIR,
    DIRECTAS_ADMIN,
    GRUPOS_ADMIN,
    RUTAS_ADMIN,
    SECCIONES_ADMIN,
    cabecera_html,
    enlaces_moviles_html,
    nombre_negocio,
    navegacion_html,
)

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
    return enlaces_moviles_html(SECCIONES_ADMIN, activa)


def _navegacion(activa: str) -> str:
    return navegacion_html(
        SECCIONES_ADMIN, activa, prefijo="orq-admin", directas=DIRECTAS_ADMIN
    )


def montar_admin(titulo: str, *, ruta_activa: str = "") -> Any:
    """Misma cabecera que la cuenta de empresa, con el menú de administración."""
    activa = _activa(ruta_activa)
    ui.html(
        cabecera_html(
            SECCIONES_ADMIN,
            activa,
            href="/admin/panel",
            etiqueta="Ir al panel",
            nombre=nombre_negocio(),
            aria_nav="Secciones del administrador",
            aria_cajon="Menú del administrador",
            accion=ACCION_EMITIR,
            directas=DIRECTAS_ADMIN,
            prefijo="orq-admin",
        ),
        sanitize=False,
    ).classes("orq-header orq-header-fijo orq-admin w-full")
    with ui.element("section").classes("orq-encabezado-pagina w-full"):
        ui.label(titulo).classes("orq-titulo")


__all__ = ["GRUPOS_ADMIN", "RUTAS_ADMIN", "SECCIONES_ADMIN", "montar_admin"]
