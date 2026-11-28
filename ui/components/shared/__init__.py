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
        f"{escape(etiqueta)}</span>"
        f'<span class="orq-total" data-valor="{escape(valor, quote=True)}">'
        f"{escape(valor)}</span></div>"
    )


def sello_emitir(numero_serie: str, titulo: str = "Emitida") -> Any:
    overlay = ui.element("div").classes("orq-sello-overlay")
    with overlay:
        ui.html(
            f'<div class="orq-sello orq-sello--gran orq-sello--emitida">'
            f"<span>{escape(titulo)}</span>"
            f"<small>{escape(numero_serie)}</small></div>"
        )
    ui.timer(1.6, overlay.delete, once=True)
    return overlay


def estado_vacio(mensaje: str, accion: str | None = None) -> Any:
    with ui.column().classes("orq-vacio w-full items-center gap-2") as contenedor:
        ui.label(mensaje).classes("orq-vacio-titulo")
        if accion:
            ui.label(accion).classes("orq-resumen")
    return contenedor


def estado_cargando(filas: int = 3) -> Any:
    with ui.column().classes("orq-cargando w-full gap-3") as contenedor:
        for _ in range(filas):
            esqueleto(20)
    return contenedor


def _valor(factura: dict[str, Any], clave: str) -> str:
    dato = factura.get(clave)
    return "" if dato is None else str(dato)


def ticket_factura(
    factura: dict[str, Any],
    columnas_lineas: list[dict[str, Any]],
    *,
    compacto: bool = False,
) -> Any:
    with ui.element("section").classes("orq-ticket w-full") as ticket:
        with ui.row().classes("orq-ticket-cabecera w-full"):
            with ui.column().classes("gap-0"):
                ui.label(_valor(factura, "numero_serie")).classes("orq-ticket-folio")
                ui.label(f"Fecha {_valor(factura, 'fecha')}").classes(
                    "orq-ticket-fecha"
                )
            sello_estado(_valor(factura, "estado"))

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
        if compacto:
            campos = tuple(campo for campo in campos if campo[1] in {
                "cliente_nombre", "cliente_ruc", "condicion_pago", "subtotal",
                "descuento_total", "itbms", "portes",
            })

        with ui.column().classes("orq-ticket-datos w-full"):
            for etiqueta, campo in campos:
                with ui.element("div").classes("orq-dato"):
                    ui.label(etiqueta).classes("orq-dato-etiqueta")
                    ui.label(_valor(factura, campo)).classes("orq-dato-valor")

        lineas = list(factura.get("lineas") or [])
        if lineas and not compacto:
            tabla_orquidea(columnas_lineas, lineas, row_key="id")

        with ui.column().classes("orq-ticket-totales"):
            total_animado(_valor(factura, "total"))

    return ticket


def ticket_resumen(
    totales: dict[str, Any],
    lineas: list[dict[str, Any]] | None = None,
    *,
    titulo: str = "Resumen de la factura",
) -> Any:
    """Ticket lateral que se actualiza mientras se llena el talonario."""
    with ui.element("section").classes("orq-ticket orq-ticket--resumen w-full") as ticket:
        ui.label(titulo).classes("orq-ticket-titulo")

        if lineas:
            with ui.column().classes("orq-resumen-lineas w-full"):
                for linea in lineas:
                    with ui.row().classes("orq-resumen-linea w-full"):
                        ui.label(str(linea.get("descripcion") or "Línea")).classes(
                            "orq-resumen-descripcion"
                        )
                        ui.label(str(linea.get("importe") or "0.00")).classes(
                            "orq-resumen-importe"
                        )

        with ui.column().classes("orq-resumen-totales w-full"):
            for etiqueta, clave in (
                ("Subtotal", "subtotal"),
                ("Descuento", "descuento_total"),
                ("ITBMS", "itbms"),
            ):
                with ui.row().classes("orq-resumen-fila w-full"):
                    ui.label(etiqueta).classes("orq-dato-etiqueta")
                    ui.label(str(totales.get(clave) or "0.00")).classes(
                        "orq-resumen-cifra"
                    )
            total_animado(str(totales.get("total") or "0.00"))
    return ticket


__all__ = [
    "esqueleto",
    "estado_cargando",
    "estado_vacio",
    "notificar",
    "sello_emitir",
    "sello_estado",
    "tabla_orquidea",
    "ticket_factura",
    "ticket_resumen",
    "total_animado",
]
