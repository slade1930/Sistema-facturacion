from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()


def consultar(cliente_api: ClienteApi, numero_serie: str, codigo: str) -> dict[str, Any]:
    return cliente_api.get(f"/api/v1/verificar/{numero_serie}/{codigo}")


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


def _describir_error(error: dict[str, Any]) -> str:
    ubicacion = ".".join(str(parte) for parte in error.get("loc", []))
    mensaje = error.get("msg") or error.get("detail") or "Valor inválido."
    return f"{ubicacion}: {mensaje}" if ubicacion else str(mensaje)


@ui.page("/verificar")
def pagina_verificar() -> None:
    montar_layout("Verificar factura")

    numero_serie = ui.input("Número de serie", placeholder="FAC-2026-0001").classes("w-full")
    codigo = ui.input(
        "Código de verificación",
        placeholder="Código impreso en la factura",
    ).classes("w-full")
    resultado = ui.column()
    mensajes = ui.column()

    def verificar() -> None:
        resultado.clear()
        mensajes.clear()

        serie = (numero_serie.value or "").strip()
        clave = (codigo.value or "").strip()
        if not serie or not clave:
            with mensajes:
                ui.label(
                    "Ingresá el número de serie y el código de verificación."
                ).classes("text-negative")
            return

        try:
            datos = consultar(cliente, serie, clave)
        except ErrorApi as error:
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
                for item in error.errors:
                    ui.label(_describir_error(item)).classes("text-caption text-negative")
            return

        with resultado:
            with ui.card().classes("w-full"):
                ui.label("Factura válida").classes("text-positive text-h6")
                campos = (
                    ("Número de serie", "numero_serie"),
                    ("Código de verificación", "codigo_verificacion"),
                    ("Fecha", "fecha"),
                    ("Cliente", "cliente_nombre"),
                    ("Total", "total"),
                    ("Estado", "estado"),
                )
                for etiqueta, campo in campos:
                    with ui.row().classes("w-full justify-between"):
                        ui.label(f"{etiqueta}:").classes("text-grey")
                        ui.label(_valor(datos, campo))

    ui.button("Verificar", on_click=verificar).classes("mt-2")
