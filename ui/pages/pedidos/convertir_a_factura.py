from typing import Any

from nicegui import ui

from components.admin.seguridad import exigir_admin
from components.forms import boton_enlace, boton_orquidea, mostrar_error, notificar
from components.layout import montar_layout
from components.shared import (
    estado_vacio,
    sello_estado,
    tabla_orquidea,
    total_animado,
)
from pages.pedidos.detalle_pedido import resumen_lineas
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()

COLUMNAS_LINEAS = (
    {"name": "producto", "label": "Producto", "field": "producto", "align": "left"},
    {"name": "cantidad", "label": "Cantidad", "field": "cantidad", "align": "right"},
    {"name": "subtotal", "label": "Subtotal", "field": "subtotal", "align": "right"},
)


def obtener_pedido(cliente_api: ClienteApi, pedido_id: int) -> dict[str, Any]:
    return cliente_api.get(f"/api/v1/pedidos/{pedido_id}")


def facturar(cliente_api: ClienteApi, pedido_id: int) -> dict[str, Any]:
    return cliente_api.post(f"/api/v1/pedidos/{pedido_id}/facturar")


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/convertir-a-factura")
def pagina_convertir(pedido_id: int | None = None) -> None:
    if not exigir_admin():
        return
    titulo = (
        f"Facturar pedido #{pedido_id}"
        if pedido_id is not None
        else "Facturar pedido"
    )
    montar_layout(
        titulo,
        ruta_activa="/pedidos/convertir-a-factura",
        migas="Pedidos por facturar",
    )

    mensajes = ui.column()
    contenido = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")
    actual: dict[str, Any] = {"pedido": None}

    def pintar_factura(factura: dict[str, Any]) -> None:
        with resultado:
            with ui.element("section").classes("orq-ticket w-full"):
                with ui.row().classes("orq-ticket-cabecera w-full"):
                    with ui.column().classes("gap-0"):
                        ui.label(_valor(factura, "numero_serie")).classes(
                            "orq-ticket-folio"
                        )
                        ui.label("Factura emitida.").classes("orq-ticket-fecha")
                    sello_estado(_valor(factura, "estado") or "emitida")

                with ui.column().classes("orq-ticket-datos w-full"):
                    campos = (
                        ("Pedido", "pedido_id"),
                        ("Cliente", "cliente_nombre"),
                        ("Número de serie", "numero_serie"),
                        ("Estado", "estado"),
                    )
                    for etiqueta, clave in campos:
                        valor = _valor(factura, clave)
                        if not valor:
                            continue
                        with ui.element("div").classes("orq-dato"):
                            ui.label(etiqueta).classes("orq-dato-etiqueta")
                            ui.label(valor).classes("orq-dato-valor")

                with ui.column().classes("orq-ticket-totales"):
                    total_animado(_valor(factura, "total"))

                with ui.row().classes("orq-ticket-acciones w-full"):
                    boton_enlace(
                        "Ver factura",
                        f"/facturacion/detalle?factura_id={_valor(factura, 'id')}",
                        variante="secundario",
                    )

        notificar(f"Factura emitida: {_valor(factura, 'numero_serie')}.")

    def convertir() -> None:
        pedido = actual["pedido"]
        if pedido is None:
            return

        mensajes.clear()
        resultado.clear()

        try:
            factura = facturar(cliente, int(pedido["id"]))
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return

        sesion.ultima_factura = factura
        pintar_factura(factura)

    def cargar() -> None:
        mensajes.clear()
        contenido.clear()
        resultado.clear()

        if pedido_id is None:
            with contenido:
                estado_vacio(
                    "Elige un pedido desde la lista para facturarlo.",
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

        actual["pedido"] = pedido
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
            for linea in resumen_lineas(pedido)
        ]

        with contenido:
            with ui.element("section").classes("orq-ticket w-full"):
                with ui.row().classes("orq-ticket-cabecera w-full"):
                    with ui.column().classes("gap-0"):
                        ui.label(
                            f"Pedido #{_valor(pedido, 'id')} · "
                            f"{_valor(pedido, 'estado')}"
                        ).classes("orq-ticket-folio")
                        ui.label("Resumen del pedido").classes("orq-ticket-fecha")
                    sello_estado(_valor(pedido, "estado"))

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

            if filas:
                tabla_orquidea(
                    list(COLUMNAS_LINEAS),
                    filas,
                    row_key="orden",
                    titulo="Líneas del pedido",
                )

            with ui.row().classes("orq-barra-acciones w-full"):
                boton_orquidea("Facturar pedido", convertir)
                boton_enlace(
                    "Ver detalle",
                    f"/pedidos/detalle?pedido_id={_valor(pedido, 'id')}",
                    variante="texto",
                )

    cargar()
