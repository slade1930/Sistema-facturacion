from typing import Any

from nicegui import ui

from components.forms import boton_enlace, mostrar_error
from components.layout import montar_layout
from components.shared import estado_vacio, sello_estado, total_animado
from pages.pedidos.convertir_a_factura import obtener_pedido
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/exitoso")
def pagina_pedido_exitoso(pedido_id: int | None = None) -> None:
    titulo = (
        f"Pedido #{pedido_id} creado"
        if pedido_id is not None
        else "Pedido creado"
    )
    montar_layout(
        titulo,
        ruta_activa="/pedidos/exitoso",
        migas="Pedidos por facturar",
    )

    mensajes = ui.column()
    contenido = ui.column().classes("w-full")

    def volver() -> None:
        with contenido:
            boton_enlace(
                "Ver pedidos por facturar",
                "/pedidos/por-facturar",
                variante="secundario",
            )

    if pedido_id is None:
        with contenido:
            estado_vacio(
                "No pudimos encontrar el pedido creado.",
                "Volvé a la lista para elegir uno.",
            )
            volver()
        return

    try:
        pedido = obtener_pedido(cliente, pedido_id)
    except ErrorApi as error:
        mostrar_error(mensajes, error)
        volver()
        return

    with contenido:
        with ui.element("section").classes("orq-ticket w-full"):
            with ui.row().classes("orq-ticket-cabecera w-full"):
                with ui.column().classes("gap-0"):
                    ui.label(f"Pedido #{_valor(pedido, 'id')}").classes(
                        "orq-ticket-folio"
                    )
                    ui.label("Creado").classes("orq-ticket-fecha")
                sello_estado(_valor(pedido, "estado") or "pendiente")

            with ui.column().classes("orq-ticket-datos w-full"):
                campos = (
                    ("Cliente", "cliente_id"),
                    ("Estado", "estado"),
                    ("Creado", "fecha_creacion"),
                )
                for etiqueta, clave in campos:
                    valor = _valor(pedido, clave)
                    if not valor:
                        continue
                    with ui.element("div").classes("orq-dato"):
                        ui.label(etiqueta).classes("orq-dato-etiqueta")
                        ui.label(valor).classes("orq-dato-valor")

                notas = _valor(pedido, "notas")
                if notas:
                    with ui.element("div").classes("orq-dato"):
                        ui.label("Notas").classes("orq-dato-etiqueta")
                        ui.label(notas).classes("orq-dato-valor")

            with ui.column().classes("orq-ticket-totales"):
                total_animado(
                    _valor(pedido, "total_estimado"),
                    etiqueta="Total estimado",
                )

        with ui.row().classes("orq-barra-acciones w-full"):
            boton_enlace(
                "Ver pedidos por facturar",
                "/pedidos/por-facturar",
                variante="secundario",
            )
            boton_enlace(
                "Convertir a factura",
                (
                    "/pedidos/convertir-a-factura"
                    f"?pedido_id={_valor(pedido, 'id')}"
                ),
            )
