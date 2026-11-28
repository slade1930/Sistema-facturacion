"""Inicio de sesión de empresa en el portal de clientes; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.auth import campos_login
from components.forms import boton_orquidea, mostrar_error, seccion_formulario
from components.forms import boton_enlace
from state import auth
from state.cliente_api import ClienteApi, ErrorApi


def enviar_login(empresa: str, contrasena: str) -> dict[str, Any]:
    return ClienteApi().post(
        "/api/v1/auth/login",
        json={"nombre_empresa": empresa, "contrasena": contrasena},
    )


def cabecera_auth() -> None:
    ui.html(
        '<header class="orq-header orq-header-fijo w-full"><div class="orq-header-inner">'
        '<a class="orq-marca" href="/"><span class="orq-nombre-marca">Orquídea</span>'
        "</a></div></header>",
        sanitize=False,
        tag="header",
    ).classes("orq-header orq-header-fijo w-full")


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
        destino = (
            "/portal/cambiar-clave"
            if respuesta.get("debe_cambiar_clave")
            else "/portal/inicio"
        )
        ui.navigate.to(destino)

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Entrar", entrar)
        boton_enlace("Crear una empresa", "/registro", variante="secundario")


__all__ = ["cabecera_auth", "enviar_login", "pagina_login"]
