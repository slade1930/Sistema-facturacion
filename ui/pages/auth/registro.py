"""Registro de empresas del portal; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.auth import campos_registro
from components.forms import boton_enlace, boton_orquidea, mostrar_error, seccion_formulario
from pages.auth.login import cabecera_auth
from state import auth
from state.cliente_api import ClienteApi, ErrorApi


def enviar_registro(datos: dict[str, Any]) -> dict[str, Any]:
    return ClienteApi().post("/api/v1/auth/registro", json=datos)


@ui.page("/registro")
def pagina_registro() -> None:
    cabecera_auth()
    with ui.element("section").classes("orq-encabezado-pagina w-full"):
        ui.label("Crear una empresa").classes("orq-titulo")
        ui.label("Tu contraseña la eliges tú; no hay valores por defecto.").classes(
            "orq-bloque-ayuda"
        )

    mensajes = ui.column().classes("w-full")
    with seccion_formulario("Datos de la empresa", rejilla=False):
        campos = campos_registro()

    async def registrar() -> None:
        mensajes.clear()
        sector = campos["sector"].value
        if not sector:
            with mensajes:
                ui.label("Elige un sector para continuar.").classes("orq-error")
            return
        datos = {
            "nombre_empresa": str(campos["nombre_empresa"].value or "").strip(),
            "ruc": str(campos["ruc"].value or "").strip(),
            "correo": str(campos["correo"].value or "").strip(),
            "direccion": str(campos["direccion"].value or "").strip() or None,
            "telefono": str(campos["telefono"].value or "").strip() or None,
            "sucursal": str(campos["sucursal"].value or "").strip() or None,
            "sector": str(sector),
            "contrasena": str(campos["contrasena"].value or ""),
        }
        try:
            respuesta = await asyncio.to_thread(enviar_registro, datos)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            with mensajes:
                ui.label(
                    "No pudimos completar el registro. Inténtalo de nuevo."
                ).classes("orq-error")
            return
        auth.guardar_sesion(respuesta)
        ui.notify("Empresa creada. Bienvenida a tu portal.")
        ui.navigate.to("/portal/inicio")

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Crear empresa", registrar)
        boton_enlace("Ya tengo cuenta", "/login", variante="secundario")


__all__ = ["enviar_registro", "pagina_registro"]
