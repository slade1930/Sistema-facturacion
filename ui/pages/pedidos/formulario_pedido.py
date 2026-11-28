from typing import Any

from nicegui import ui

from components.forms import (
    boton_enlace,
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    seccion_formulario,
    selector_orquidea,
)
from components.layout import montar_layout
from components.shared import estado_vacio, ticket_resumen
from pages.catalogo.carrito import calcular as calcular_carrito
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()


def listar_clientes(cliente_api: ClienteApi, busqueda: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"solo_activos": True}
    if busqueda:
        params["busqueda"] = busqueda
    return cliente_api.get("/api/v1/clientes", params=params)


def construir_lineas(
    carrito: list[dict[str, Any]], calculo: dict[str, Any]
) -> list[dict[str, Any]]:
    por_clave = {
        (str(linea["producto_id"]), linea["tipo_empaque"]): linea
        for linea in calculo.get("lineas", [])
    }
    lineas = []
    for orden, item in enumerate(carrito, start=1):
        clave = (str(item["producto_id"]), item["tipo_empaque"])
        calculada = por_clave.get(clave)
        if calculada is None:
            raise ValueError(f"No hay precio calculado para {item['nombre']}.")
        lineas.append(
            {
                "producto_id": int(item["producto_id"]),
                "tipo_empaque": item["tipo_empaque"],
                "cantidad": str(item["cantidad"]),
                "subtotal": str(calculada["subtotal"]),
                "orden": orden,
            }
        )
    return lineas


def construir_pedido(
    cliente_id: int,
    notas: str | None,
    carrito: list[dict[str, Any]],
    calculo: dict[str, Any],
) -> dict[str, Any]:
    lineas = construir_lineas(carrito, calculo)
    if not lineas:
        raise ValueError("El carrito está vacío.")
    notas_limpias = (notas or "").strip() or None
    return {
        "cliente_id": int(cliente_id),
        "estado": "pendiente",
        "total_estimado": str(calculo.get("subtotal", "0")),
        "notas": notas_limpias,
        "lineas": lineas,
    }


def crear_pedido(cliente_api: ClienteApi, payload: dict[str, Any]) -> dict[str, Any]:
    return cliente_api.post("/api/v1/pedidos", json=payload)


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/formulario")
def pagina_formulario_pedido() -> None:
    montar_layout(
        "Armar un pedido", ruta_activa="/pedidos/formulario", migas="Productos"
    )
    ui.label("Formulario de pedido").classes("orq-ayuda")

    mensajes = ui.column()
    calculo_actual: dict[str, Any] = {}

    with ui.element("div").classes("orq-dos-columnas w-full"):
        with ui.column().classes("w-full gap-4"):
            with seccion_formulario(
                "Datos del pedido",
                "Elegí el cliente y sumá una nota si el pedido necesita una indicación.",
            ):
                clientes = selector_orquidea(
                    "Cliente", {0: "Seleccione un cliente"}, value=0
                ).classes("w-full")
                notas = campo_orquidea(
                    "Notas", placeholder="Entrega, horario o referencias"
                ).classes("w-full")
        with ui.column().classes("w-full"):
            resumen = ui.column().classes("w-full")

    def cargar_clientes() -> None:
        try:
            datos = listar_clientes(cliente)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return

        opciones: dict[Any, str] = {0: "Seleccione un cliente"}
        for item in datos:
            opciones[int(item["id"])] = _valor(item, "nombre_empresa")
        clientes.options = opciones
        clientes.update()

    def cargar_resumen() -> None:
        resumen.clear()
        calculo_actual.clear()

        if not sesion.carrito:
            with resumen:
                estado_vacio(
                    "El carrito está vacío.",
                    "Agregá productos desde el catálogo antes de armar el pedido.",
                )
            return

        try:
            calculo = calcular_carrito(cliente, sesion.carrito)
        except ErrorApi as error:
            mostrar_error(resumen, error)
            return

        calculo_actual.update(calculo)
        lineas = [
            {
                "descripcion": (
                    f"{_valor(linea, 'descripcion')} · "
                    f"{_valor(linea, 'cantidad')} × "
                    f"{_valor(linea, 'precio_unitario')}"
                ),
                "importe": _valor(linea, "subtotal"),
            }
            for linea in calculo.get("lineas", [])
        ]

        with resumen:
            ticket_resumen(calculo, lineas, titulo="Resumen del carrito")
            ui.label(
                f"Total estimado: {_valor(calculo, 'subtotal')}"
            ).classes("orq-resumen mt-2")

    def guardar() -> None:
        mensajes.clear()

        if not clientes.value:
            with mensajes:
                ui.label("Elegí un cliente para continuar.").classes("orq-error")
            return
        if not calculo_actual:
            with mensajes:
                ui.label("No se pudo calcular el carrito.").classes("orq-error")
            return

        try:
            payload = construir_pedido(
                int(clientes.value), notas.value, sesion.carrito, calculo_actual
            )
        except ValueError as error:
            with mensajes:
                ui.label(str(error)).classes("orq-error")
            return

        try:
            pedido = crear_pedido(cliente, payload)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return

        sesion.carrito.clear()
        ui.navigate.to(f"/pedidos/exitoso?pedido_id={pedido['id']}")

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Crear pedido", guardar)
        boton_enlace("Volver al carrito", "/carrito", variante="secundario")

    cargar_clientes()
    cargar_resumen()
