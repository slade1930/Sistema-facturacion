"""Datos y clave de la cuenta de la empresa. Rol empresa; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.forms import boton_enlace, boton_orquidea, mostrar_error
from components.portal import montar_portal, salir
from components.shared import estado_cargando, estado_vacio
from state import auth
from state.cliente_api import ErrorApi

SECTORES = auth.SECTORES


def consultar(api: Any) -> dict[str, Any]:
    return api.get("/api/v1/auth/yo")


@ui.page("/portal/mi-cuenta")
async def pagina_mi_cuenta() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Mi cuenta", ruta_activa="/portal/mi-cuenta")

    mensajes = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")
    with resultado:
        estado_cargando(3)

    async def cargar() -> None:
        mensajes.clear()
        try:
            datos = await asyncio.to_thread(consultar, auth.cliente_portal())
        except ErrorApi as error:
            resultado.clear()
            mostrar_error(mensajes, error)
            return
        except Exception:
            resultado.clear()
            with mensajes:
                ui.label("No pudimos cargar tu cuenta.").classes("orq-error")
            return
        empresa = datos.get("empresa") or {}
        resultado.clear()
        if not empresa:
            with resultado:
                estado_vacio(
                    "Tu cuenta no tiene una empresa asociada.",
                    "Si eres administrador, usa la interfaz de facturación.",
                )
            return
        with resultado:
            with ui.element("section").classes("orq-ticket w-full"):
                ui.label(str(empresa.get("nombre") or "")).classes("orq-ticket-titulo")
                campos = (
                    ("RUC", empresa.get("ruc")),
                    ("Sucursal", empresa.get("sucursal") or "—"),
                    (
                        "Sector",
                        SECTORES.get(str(empresa.get("sector") or ""), "—"),
                    ),
                )
                for etiqueta, valor in campos:
                    with ui.element("div").classes("orq-dato"):
                        ui.label(etiqueta).classes("orq-dato-etiqueta")
                        ui.label(str(valor or "")).classes("orq-dato-valor")
                if datos.get("debe_cambiar_clave"):
                    ui.label("Debes actualizar tu contraseña.").classes("orq-error")
                ui.label(f"Cuenta #{datos.get('cuenta_id') or ''}").classes(
                    "orq-bloque-ayuda"
                )
            with ui.row().classes("orq-barra-acciones w-full"):
                boton_enlace(
                    "Cambiar contraseña",
                    "/portal/cambiar-clave",
                    variante="secundario",
                )
                boton_orquidea("Salir", salir, variante="texto")

    asyncio.create_task(cargar())


__all__ = ["consultar", "pagina_mi_cuenta"]
