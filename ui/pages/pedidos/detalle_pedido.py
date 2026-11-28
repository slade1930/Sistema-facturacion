from typing import Any

from nicegui import app, ui

from components.forms import boton_enlace, mostrar_error
from components.layout import montar_layout
from components.shared import (
    estado_vacio,
    sello_estado,
    tabla_orquidea,
    total_animado,
)
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import conectar_storage

cliente = ClienteApi()

ENVASES = {
    "caja": "Caja",
    "media_caja": "Media caja",
    "unidad": "Unidad",
}

COLUMNAS_LINEAS = (
    {"name": "producto", "label": "Producto", "field": "producto", "align": "left"},
    {"name": "cantidad", "label": "Cantidad", "field": "cantidad", "align": "right"},
    {"name": "subtotal", "label": "Subtotal", "field": "subtotal", "align": "right"},
)


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
async def pagina_detalle_pedido(pedido_id: int | None = None) -> None:
    await conectar_storage()
    titulo = (
        f"Pedido #{pedido_id}"
        if pedido_id is not None
        else "Detalle del pedido"
    )
    montar_layout(
        titulo,
        ruta_activa="/pedidos/detalle",
        migas="Pedidos por facturar",
    )

    mensajes = ui.column()
    contenido = ui.column().classes("w-full")

    def cargar() -> None:
        mensajes.clear()
        contenido.clear()

        if pedido_id is None:
            with contenido:
                estado_vacio(
                    "Elige un pedido desde la lista para ver el detalle.",
                    "Vuelve a pedidos por facturar para continuar.",
                )
                boton_enlace(
                    "Ver pedidos por facturar",
                    "/pedidos/por-facturar",
                    variante="secundario",
                )
            return

        try:
            pedido = obtener_pedido(cliente, pedido_id)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            with contenido:
                boton_enlace(
                    "Ver pedidos por facturar",
                    "/pedidos/por-facturar",
                    variante="secundario",
                )
            return

        lineas = resumen_lineas(pedido)
        filas = [
            {
                "orden": linea["orden"],
                "producto": (
                    f"Producto #{linea['producto_id']} · "
                    f"{linea['presentacion']}"
                ),
                "cantidad": linea["cantidad"],
                "subtotal": linea["subtotal"],
            }
            for linea in lineas
        ]

        with contenido:
            with ui.element("section").classes("orq-ticket w-full"):
                with ui.row().classes("orq-ticket-cabecera w-full"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"Pedido #{_valor(pedido, 'id')}").classes(
                            "orq-ticket-folio"
                        )
                        ui.label("Detalle del pedido").classes("orq-ticket-fecha")
                    sello_estado(_valor(pedido, "estado"))

                with ui.column().classes("orq-ticket-datos w-full"):
                    campos = (
                        ("Cliente", "cliente_id"),
                        ("Estado", "estado"),
                        ("Creado", "fecha_creacion"),
                        ("Actualizado", "fecha_actualizacion"),
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

            if filas:
                tabla_orquidea(
                    list(COLUMNAS_LINEAS),
                    filas,
                    row_key="orden",
                    titulo="Líneas del pedido",
                )
            else:
                with ui.column().classes("w-full mt-4"):
                    estado_vacio("Este pedido todavía no tiene líneas.")

            with ui.row().classes("orq-barra-acciones w-full"):
                boton_enlace(
                    "Convertir a factura",
                    (
                        "/pedidos/convertir-a-factura"
                        f"?pedido_id={_valor(pedido, 'id')}"
                    ),
                )
                boton_enlace(
                    "Ver pedidos por facturar",
                    "/pedidos/por-facturar",
                    variante="texto",
                )

    cargar()

    aviso = app.storage.tab.pop("aviso", None)
    if aviso:
        with mensajes:
            ui.label(str(aviso)).classes("text-positive")
