
from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()


def obtener_pedido(cliente_api: ClienteApi, pedido_id: int) -> dict[str, Any]:
    return cliente_api.get(f"/api/v1/pedidos/{pedido_id}")


def facturar(cliente_api: ClienteApi, pedido_id: int) -> dict[str, Any]:
    return cliente_api.post(f"/api/v1/pedidos/{pedido_id}/facturar")


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/convertir-a-factura")
def pagina_convertir(pedido_id: int | None = None) -> None:
    montar_layout("Convertir pedido a factura")

    entrada = ui.input(
        "ID del pedido", value=str(pedido_id) if pedido_id is not None else ""
    )
    ui.button("Cargar", on_click=lambda: cargar()).classes("mt-2")
    mensajes = ui.column()
    pedido_card = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")
    actual: dict[str, Any] = {"pedido": None}

    def mostrar_error(error: ErrorApi) -> None:
        mensajes.clear()
        with mensajes:
            ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            for item in error.errors:
                ui.label(str(item)).classes("text-caption text-negative")

    def cargar() -> None:
        mensajes.clear()
        pedido_card.clear()
        resultado.clear()
        texto = (entrada.value or "").strip()

        if not texto.isdigit():
            with mensajes:
                ui.label("Ingresá un ID numérico de pedido.").classes("text-negative")
            return

        try:
            pedido = obtener_pedido(cliente, int(texto))
        except ErrorApi as error:
            mostrar_error(error)
            return

        actual["pedido"] = pedido

        with pedido_card:
            ui.button(
                "Volver al detalle",
                on_click=lambda: ui.navigate.to(
                    f"/pedidos/detalle?pedido_id={pedido['id']}"
                ),
            ).classes("mb-2")

            with ui.card().classes("w-full"):
                ui.label(
                    f"Pedido #{_valor(pedido, 'id')} · {_valor(pedido, 'estado')}"
                ).classes("text-h6")

                campos = (
                    ("Cliente ID", "cliente_id"),
                    ("Total estimado", "total_estimado"),
                    ("Notas", "notas"),
                    ("Factura generada", "factura_generada_id"),
                    ("Creado", "fecha_creacion"),
                )

                for etiqueta, campo in campos:
                    with ui.row().classes("w-full justify-between"):
                        ui.label(f"{etiqueta}:").classes("text-grey")
                        ui.label(_valor(pedido, campo))

                ui.button(
                    "Facturar pedido",
                    on_click=lambda: convertir(),
                ).classes("mt-2")

    def convertir() -> None:
        pedido = actual["pedido"]
        if pedido is None:
            return

        mensajes.clear()
        resultado.clear()

        try:
            factura = facturar(cliente, int(pedido["id"]))
        except ErrorApi as error:
            mostrar_error(error)
            return

        sesion.ultima_factura = factura

        with resultado:
            with ui.card().classes("w-full"):
                ui.label(
                    f"Factura {_valor(factura, 'numero_serie')} creada"
                ).classes("text-positive text-h6")

                with ui.row().classes("w-full justify-between"):
                    ui.label("Total").classes("text-grey")
                    ui.label(_valor(factura, "total"))

                with ui.row().classes("w-full justify-between"):
                    ui.label("Estado").classes("text-grey")
                    ui.label(_valor(factura, "estado"))

                ui.link(
                    "Ver factura",
                    f"/facturacion/detalle?id={factura['id']}",
                ).classes("mt-2")

    if pedido_id is not None:
        cargar()
