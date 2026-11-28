"""Cambio de contraseña de la cuenta del portal; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.auth import indicador_clave
from components.forms import (
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    seccion_formulario,
)
from components.portal import montar_portal
from state import auth
from state.cliente_api import ErrorApi


def enviar_cambio(actual: str, nueva: str) -> dict[str, Any]:
    return auth.cliente_portal().post(
        "/api/v1/auth/cambiar-clave",
        json={"contrasena_actual": actual, "contrasena_nueva": nueva},
    )


@ui.page("/portal/cambiar-clave")
async def pagina_cambiar_clave() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Cambiar contraseña", ruta_activa="/portal/mi-cuenta")

    mensajes = ui.column().classes("w-full")
    with seccion_formulario("Tu contraseña", rejilla=False):
        actual = campo_orquidea("Contraseña actual", password=True)
        nueva = campo_orquidea("Nueva contraseña", password=True)
        indicador_clave(nueva)

    async def guardar() -> None:
        mensajes.clear()
        try:
            respuesta = await asyncio.to_thread(
                enviar_cambio,
                str(actual.value or ""),
                str(nueva.value or ""),
            )
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            with mensajes:
                ui.label(
                    "No pudimos cambiar la contraseña. Inténtalo de nuevo."
                ).classes("orq-error")
            return
        ui.notify(str(respuesta.get("detalle") or "Contraseña actualizada."))
        ui.navigate.to("/portal/inicio")

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Guardar contraseña", guardar)


__all__ = ["enviar_cambio", "pagina_cambiar_clave"]
