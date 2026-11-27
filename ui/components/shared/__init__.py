from html import escape
from typing import Any

from nicegui import ui

from components.forms import esqueleto, notificar
from components.tables import tabla_orquidea

SELLOS = {
    "emitida": ("Emitida", "orq-sello--emitida"),
    "anulada": ("Anulada", "orq-sello--anulada"),
    "en_revision": ("En revisión", "orq-sello--revision"),
    "pendiente": ("Pendiente", "orq-sello--neutro"),
}


def sello_estado(estado: str) -> Any:
    texto, clase = SELLOS.get(estado, (estado.capitalize(), "orq-sello--neutro"))
    return ui.html(f'<span class="orq-sello {clase}">{escape(texto)}</span>')


def total_animado(valor: str, etiqueta: str = "Total") -> Any:
    return ui.html(
        f'<div class="orq-dato"><span class="orq-dato-etiqueta">'
        f'{escape(etiqueta)}</span>'
        f'<span class="orq-total" data-valor="{escape(valor, quote=True)}">'
        f'{escape(valor)}</span></div>'
    )


def sello_emitir(numero_serie: str, titulo: str = "Emitida") -> Any:
    overlay = ui.element("div").classes("orq-sello-overlay")
    with overlay:
        ui.html(
            f'<div class="orq-sello orq-sello--gran orq-sello--emitida">'
            f'<span>{escape(titulo)}</span>'
            f'<small>{escape(numero_serie)}</small></div>'
        )
    ui.timer(1.6, overlay.delete, once=True)
    return overlay


def estado_vacio(mensaje: str, accion: str | None = None) -> Any:
    with ui.column().classes("orq-vacio w-full items-center gap-2") as contenedor:
        ui.label("Aún no hay facturas.").classes("")
        ui.label(mensaje)
        if accion:
            ui.label(accion).classes("orq-resumen")
    return contenedor


def ticket_factura(
    factura: dict[str, Any],
    columnas_lineas: list[dict[str, Any]],
) -> Any:
    def valor(clave: str) -> str:
        dato = factura.get(clave)
        return "" if dato is None else str(dato)

    with ui.element("section").classes("orq-ticket w-full") as ticket:
        with ui.row().classes("orq-ticket-cabecera w-full"):
            with ui.column().classes("gap-0"):
                ui.label(valor("numero_serie")).classes("orq-ticket-folio")
                ui.label(f"Fecha {valor('fecha')}").classes("orq-ticket-fecha")
            sello_estado(valor("estado"))

        campos = (
            ("Cliente", "cliente_nombre"),
            ("RUC", "cliente_ruc"),
            ("Condición", "condicion_pago"),
            ("Subtotal", "subtotal"),
            ("Descuento", "descuento_total"),
            ("Base gravada", "base_gravada"),
            ("Base exenta", "base_exenta"),
            ("ITBMS", "itbms"),
            ("Portes", "portes"),
            ("Orden de compra", "orden_compra"),
            ("Código de verificación", "codigo_verificacion"),
            ("Notas", "notas"),
        )
        with ui.column().classes("orq-ticket-datos w-full"):
            for etiqueta, campo in campos:
                with ui.element("div").classes("orq-dato"):
                    ui.label(etiqueta).classes("orq-dato-etiqueta")
                    ui.label(valor(campo)).classes("orq-dato-valor")

        lineas = list(factura.get("lineas") or [])
        if lineas:
            tabla_orquidea(columnas_lineas, lineas, row_key="id")

        with ui.column().classes("orq-ticket-totales"):
            total_animado(valor("total"))

    return ticket


__all__ = [
    "esqueleto",
    "estado_vacio",
    "notificar",
    "sello_emitir",
    "sello_estado",
    "tabla_orquidea",
    "ticket_factura",
    "total_animado",
]
