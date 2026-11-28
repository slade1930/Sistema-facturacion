from typing import Any

from nicegui import ui

from components.forms import (
    boton_orquidea,
    campo_orquidea,
    mensaje_error,
    mostrar_error,
    notificar,
    seccion_formulario,
)
from components.layout import montar_layout
from components.shared import sello_emitir, sello_estado, total_animado
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()

REVISAR = "Revisá el número de serie y el código impresos en la factura."


def consultar(cliente_api: ClienteApi, numero_serie: str, codigo: str) -> dict[str, Any]:
    return cliente_api.get(f"/api/v1/verificar/{numero_serie}/{codigo}")


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/verificar")
def pagina_verificar(numero_serie: str = "", codigo: str = "") -> None:
    montar_layout("Comprobar una factura", ruta_activa="/verificar")

    with seccion_formulario(
        "Datos de la factura", "Tomá los valores impresos en el comprobante.",
        rejilla=False,
    ):
        with ui.element("div").classes("orq-dos-columnas w-full"):
            entrada_serie = campo_orquidea(
                "Número de serie", placeholder="FAC-2026-0001"
            ).classes("w-full")
            entrada_codigo = campo_orquidea(
                "Código de verificación", placeholder="El que aparece en la factura"
            ).classes("w-full")

    mensajes = ui.column().classes("w-full gap-1")
    resultado = ui.column().classes("w-full")

    def verificar() -> None:
        resultado.clear()
        mensajes.clear()

        serie = (entrada_serie.value or "").strip()
        clave = (entrada_codigo.value or "").strip()
        if not serie or not clave:
            with mensajes:
                mensaje_error(REVISAR)
            return

        try:
            datos = consultar(cliente, serie, clave)
        except ErrorApi as error:
            with mensajes:
                mostrar_error(mensajes, error)
            return
        except Exception:
            with mensajes:
                mensaje_error(REVISAR)
            notificar(REVISAR, "warning")
            return

        if not isinstance(datos, dict) or datos.get("valida") is False:
            with mensajes:
                mensaje_error(REVISAR)
            notificar(REVISAR, "warning")
            return

        with resultado:
            with ui.element("section").classes("orq-ticket w-full"):
                with ui.row().classes("orq-ticket-cabecera w-full"):
                    with ui.column().classes("gap-0"):
                        ui.label(_valor(datos, "numero_serie") or serie).classes(
                            "orq-ticket-folio"
                        )
                        ui.label("Factura válida").classes("orq-ticket-fecha")
                    sello_estado(_valor(datos, "estado") or "emitida")

                with ui.column().classes("orq-ticket-datos w-full"):
                    for etiqueta, campo in (
                        ("Código de verificación", "codigo_verificacion"),
                        ("Fecha", "fecha"),
                        ("Cliente", "cliente_nombre"),
                    ):
                        with ui.element("div").classes("orq-dato"):
                            ui.label(etiqueta).classes("orq-dato-etiqueta")
                            ui.label(_valor(datos, campo)).classes("orq-dato-valor")

                with ui.column().classes("orq-ticket-totales"):
                    total_animado(_valor(datos, "total"))

        sello_emitir(_valor(datos, "numero_serie") or serie, titulo="Válida")
        notificar("Factura válida. Los datos coinciden con el registro.")

    boton_orquidea("Verificar", verificar, variante="primario")

    serie_inicial = (numero_serie or "").strip()
    clave_inicial = (codigo or "").strip()
    if serie_inicial and clave_inicial:
        entrada_serie.value = serie_inicial
        entrada_codigo.value = clave_inicial
        verificar()
