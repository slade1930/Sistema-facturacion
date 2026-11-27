
from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()

ENVASES = {
    "caja": "Caja",
    "media_caja": "Media caja",
    "unidad": "Unidad",
}


def obtener_pedido(cliente_api: ClienteApi, pedido_id: int) -> dict[str, Any]:
    return cliente_api.get(f"/api/v1/pedidos/{pedido_id}")


def resumen_lineas(pedido: dict[str, Any]) -> list[dict[str, str]]:
    lineas = []
    for linea in pedido.get("lineas", []):
        tipo = str(linea.get("tipo_empaque", ""))
        lineas.append(
            {
                "orden": str(linea.get("orden", "")),
                "producto_id": str(linea.get("producto_id", "")),
                "presentacion": ENVASES.get(tipo, tipo),
                "cantidad": str(linea.get("cantidad", "")),
                "subtotal": str(linea.get("subtotal", "")),
            }
        )
    return lineas


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/detalle")
def pagina_detalle_pedido(pedido_id: int | None = None) -> None:
    montar_layout("Detalle de pedido")

    mensajes = ui.column()
    entrada = ui.input(
        "ID del pedido", value=str(pedido_id) if pedido_id is not None else ""
    )
    ui.button("Cargar", on_click=lambda: cargar()).classes("mt-2")
    contenido = ui.column().classes("w-full")

    def mostrar_error(error: ErrorApi) -> None:
        mensajes.clear()
        with mensajes:
            ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            for item in error.errors:
                ui.label(str(item)).classes("text-caption text-negative")

    def cargar() -> None:
        mensajes.clear()
        contenido.clear()
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

        with contenido:
            ui.button(
                "Volver a pedidos pendientes",
                on_click=lambda: ui.navigate.to("/pedidos/por-facturar"),
            ).classes("mb-2")

            with ui.card().classes("w-full"):
                ui.label(f"Pedido #{_valor(pedido, 'id')}").classes("text-h6")
                campos = (
                    ("Cliente ID", "cliente_id"),
                    ("Estado", "estado"),
                    ("Total estimado", "total_estimado"),
                    ("Factura generada", "factura_generada_id"),
                    ("Creado", "fecha_creacion"),
                    ("Actualizado", "fecha_actualizacion"),
                )

                for etiqueta, clave in campos:
                    with ui.row().classes("w-full justify-between"):
                        ui.label(f"{etiqueta}:").classes("text-grey")
                        ui.label(_valor(pedido, clave))

                notas = _valor(pedido, "notas")
                if notas:
                    ui.label(f"Notas: {notas}").classes("text-caption")

            ui.label("Líneas").classes("text-h6 mt-2")
            lineas = resumen_lineas(pedido)

            if not lineas:
                ui.label("El pedido no tiene líneas.").classes("text-grey")

            for linea in lineas:
                with ui.card().classes("w-full"):
                    ui.label(
                        f"{linea['orden']}. Producto #{linea['producto_id']} · "
                        f"{linea['presentacion']}"
                    ).classes("text-subtitle1")

                    with ui.row().classes("w-full justify-between"):
                        ui.label("Cantidad").classes("text-grey")
                        ui.label(linea["cantidad"])

                    with ui.row().classes("w-full justify-between"):
                        ui.label("Subtotal").classes("text-grey")
                        ui.label(linea["subtotal"])

            with ui.row().classes("gap-2 mt-2"):
                ui.button(
                    "Convertir a factura",
                    on_click=lambda: ui.navigate.to(
                        f"/pedidos/convertir-a-factura?pedido_id={pedido['id']}"
                    ),
                )

    if pedido_id is not None:
        cargar()
