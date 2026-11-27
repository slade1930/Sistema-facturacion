from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()


def listar_pendientes(cliente_api: ClienteApi, limite: int = 100) -> list[dict[str, Any]]:
    return cliente_api.get(
        "/api/v1/pedidos/por-facturar",
        params={"limite": limite},
    )


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/por-facturar")
def pagina_pedidos_pendientes(limite: int = 100) -> None:
    montar_layout("Pedidos por facturar")

    mensajes = ui.column()
    contenedor = ui.column().classes("w-full")

    def cargar() -> None:
        mensajes.clear()
        contenedor.clear()
        try:
            pedidos = listar_pendientes(cliente, limite)
        except ErrorApi as error:
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            return

        if not pedidos:
            with contenedor:
                ui.label("No hay pedidos pendientes de facturar.").classes("text-grey")
            return

        for pedido in pedidos:
            with contenedor:
                with ui.card().classes("w-full"):
                    ui.label(
                        f"Pedido #{_valor(pedido, 'id')} · {_valor(pedido, 'estado')}"
                    ).classes("text-h6")
                    with ui.row().classes("w-full justify-between"):
                        ui.label("Cliente").classes("text-grey")
                        ui.label(_valor(pedido, "cliente_id"))
                    with ui.row().classes("w-full justify-between"):
                        ui.label("Total estimado").classes("text-grey")
                        ui.label(_valor(pedido, "total_estimado"))
                    with ui.row().classes("w-full justify-between"):
                        ui.label("Líneas").classes("text-grey")
                        ui.label(str(len(pedido.get("lineas", []))))
                    notas = _valor(pedido, "notas")
                    if notas:
                        ui.label(f"Notas: {notas}").classes("text-caption")
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button(
                            "Ver detalle",
                            on_click=lambda p=pedido: ui.navigate.to(
                                f"/pedidos/detalle?id={p['id']}"
                            ),
                        )
                        ui.button(
                            "Facturar",
                            on_click=lambda p=pedido: ui.navigate.to(
                                f"/pedidos/convertir-a-factura?id={p['id']}"
                            ),
                        )

    cargar()
