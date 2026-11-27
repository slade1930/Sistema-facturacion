
from typing import Any

from nicegui import ui

from components.layout import montar_layout
from pages.pedidos.convertir_a_factura import obtener_pedido
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/exitoso")
def pagina_pedido_exitoso(pedido_id: int | None = None) -> None:
    montar_layout("Pedido creado")

    mensajes = ui.column()
    contenido = ui.column().classes("w-full")

    if pedido_id is None:
        with mensajes:
            ui.label("Falta el ID del pedido creado.").classes("text-negative")
        return

    try:
        pedido = obtener_pedido(cliente, pedido_id)
    except ErrorApi as error:
        with mensajes:
            ui.label(f"{error.code}: {error.detail}").classes("text-negative")
        return

    with contenido:
        with ui.card().classes("w-full"):
            ui.label(f"Pedido #{_valor(pedido, 'id')} creado").classes(
                "text-positive text-h6"
            )
            campos = (
                ("Cliente ID", "cliente_id"),
                ("Estado", "estado"),
                ("Total estimado", "total_estimado"),
                ("Notas", "notas"),
                ("Creado", "fecha_creacion"),
            )
            for etiqueta, campo in campos:
                with ui.row().classes("w-full justify-between"):
                    ui.label(f"{etiqueta}:").classes("text-grey")
                    ui.label(_valor(pedido, campo))
            with ui.row().classes("gap-2 mt-2"):
                ui.link("Ver pedidos por facturar", "/pedidos/por-facturar")
                ui.link(
                    "Convertir a factura",
                    f"/pedidos/convertir-a-factura?pedido_id={pedido['id']}",
                )
