from typing import Any

from nicegui import ui

from components.forms import boton_orquidea, campo_orquidea, mensaje_error, notificar
from components.layout import montar_layout
from components.shared import sello_emitir, sello_estado, total_animado
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
    montar_layout("Verificar")

    with ui.column().classes("w-full gap-3"):
        numero_serie = campo_orquidea(
            "Número de serie", placeholder="FAC-2026-0001"
        ).classes("w-full")
        codigo = campo_orquidea(
            "Código de verificación", placeholder="Código impreso en la factura"
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
                mensaje_error("Ingresá el número de serie y el código de verificación.")
            return

        try:
            datos = consultar(cliente, serie, clave)
        except ErrorApi as error:
            with mensajes:
                mensaje_error(f"{error.code}: {error.detail}")
                for item in error.errors:
                    mensaje_error(_describir_error(item))
            notificar(f"No se pudo verificar: {error.detail}.", "negative")
            return

        with resultado:
            with ui.element("section").classes("orq-ticket w-full") as ticket:
                with ui.row().classes("orq-ticket-cabecera w-full"):
                    with ui.column().classes("gap-0"):
                        ui.label(_valor(datos, "numero_serie")).classes(
                            "orq-ticket-folio"
                        )
                        ui.label("Factura válida").classes("orq-ticket-fecha")
                    sello_estado(_valor(datos, "estado") or "emitida")
                campos = (
                    ("Código de verificación", "codigo_verificacion"),
                    ("Fecha", "fecha"),
                    ("Cliente", "cliente_nombre"),
                )
                with ui.column().classes("orq-ticket-datos w-full"):
                    for etiqueta, campo in campos:
                        with ui.element("div").classes("orq-dato"):
                            ui.label(etiqueta).classes("orq-dato-etiqueta")
                            ui.label(_valor(datos, campo)).classes("orq-dato-valor")
                with ui.column().classes("orq-ticket-totales"):
                    total_animado(_valor(datos, "total"))
        sello_emitir(_valor(datos, "numero_serie") or serie, titulo="Válida")
        notificar("Factura válida. Los datos coinciden con el registro.")

    with ui.row().classes("mt-1"):
        boton_orquidea("Verificar", verificar, variante="primario")
