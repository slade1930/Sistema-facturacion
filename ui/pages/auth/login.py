"""Inicio de sesión del negocio y de las cuentas de empresa; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.auth import campos_login
from components.forms import boton_orquidea, mostrar_error, seccion_formulario
from components.forms import boton_enlace
from components.sesion import cabecera_publica, destino_sesion
from state import auth
from state.cliente_api import ClienteApi, ErrorApi


def enviar_login(empresa: str, contrasena: str) -> dict[str, Any]:
    return ClienteApi().post(
        "/api/v1/auth/login",
        json={"nombre_empresa": empresa, "contrasena": contrasena},
    )


def cabecera_auth() -> None:
    cabecera_publica()


@ui.page("/login")
def pagina_login() -> None:
    cabecera_auth()
    with ui.element("section").classes("orq-encabezado-pagina w-full"):
        ui.label("Entrar al portal").classes("orq-titulo")
        ui.label("Usa el nombre de tu empresa y tu contraseña.").classes(
            "orq-bloque-ayuda"
        )

    mensajes = ui.column().classes("w-full")
    with seccion_formulario("Tus datos", rejilla=False):
        campos = campos_login()

    async def entrar() -> None:
        mensajes.clear()
        empresa = str(campos["empresa"].value or "").strip()
        contrasena = str(campos["contrasena"].value or "")
        if not empresa or not contrasena:
            with mensajes:
                ui.label("Ingresa la empresa y la contraseña.").classes("orq-error")
            return
        try:
            respuesta = await asyncio.to_thread(enviar_login, empresa, contrasena)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            with mensajes:
                ui.label(
                    "No pudimos conectar con el sistema. Inténtalo de nuevo."
                ).classes("orq-error")
            return
        auth.guardar_sesion(respuesta)
        ui.notify("Sesión iniciada.")
        ui.navigate.to(destino_sesion(respuesta))

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Entrar", entrar)
        boton_enlace("Crear una empresa", "/registro", variante="secundario")


__all__ = ["cabecera_auth", "enviar_login", "pagina_login"]
