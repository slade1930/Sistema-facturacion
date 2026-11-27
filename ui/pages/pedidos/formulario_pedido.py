from typing import Any

from nicegui import ui

from components.layout import montar_layout
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
    notas_limpas = (notas or "").strip() or None
    return {
        "cliente_id": int(cliente_id),
        "estado": "pendiente",
        "total_estimado": str(calculo.get("subtotal", "0")),
        "notas": notas_limpas,
        "lineas": lineas,
    }


def crear_pedido(cliente_api: ClienteApi, payload: dict[str, Any]) -> dict[str, Any]:
    return cliente_api.post("/api/v1/pedidos", json=payload)


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/pedidos/formulario")
def pagina_formulario_pedido() -> None:
    montar_layout("Formulario de pedido")

    mensajes = ui.column()
    clientes = ui.select({0: "Seleccione un cliente"}, label="Cliente", value=0)
    notas = ui.input("Notas").classes("w-full")
    resumen = ui.column().classes("w-full")
    calculo_actual: dict[str, Any] = {}

    def cargar_clientes() -> None:
        try:
            datos = listar_clientes(cliente)
        except ErrorApi as error:
            mensajes.clear()
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            return
        opciones: dict[Any, str] = {0: "Seleccione un cliente"}
        for item in datos:
            opciones[item["id"]] = item["nombre_empresa"]
        clientes.options = opciones
        clientes.update()

    def cargar_resumen() -> None:
        resumen.clear()
        calculo_actual.clear()
        if not sesion.carrito:
            with resumen:
                ui.label("El carrito está vacío.").classes("text-grey")
            return
        try:
            calculo = calcular_carrito(cliente, sesion.carrito)
        except ErrorApi as error:
            with resumen:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            return
        calculo_actual.update(calculo)
        with resumen:
            with ui.card().classes("w-full"):
                ui.label("Resumen del carrito").classes("text-h6")
                for linea in calculo.get("lineas", []):
                    ui.label(
                        f"{linea['descripcion']} · {linea['cantidad']} "
                        f"× {linea['precio_unitario']} = {linea['subtotal']}"
                    )
                with ui.row().classes("w-full justify-between"):
                    ui.label("Subtotal").classes("text-grey")
                    ui.label(_valor(calculo, "subtotal"))
                with ui.row().classes("w-full justify-between"):
                    ui.label("Total estimado").classes("text-grey")
                    ui.label(_valor(calculo, "total"))

    def guardar() -> None:
        mensajes.clear()
        if not clientes.value:
            with mensajes:
                ui.label("Seleccione un cliente.").classes("text-negative")
            return
        if not calculo_actual:
            with mensajes:
                ui.label("No se pudo calcular el carrito.").classes("text-negative")
            return
        try:
            payload = construir_pedido(
                int(clientes.value), notas.value, sesion.carrito, calculo_actual
            )
        except ValueError as error:
            with mensajes:
                ui.label(str(error)).classes("text-negative")
            return
        try:
            pedido = crear_pedido(cliente, payload)
        except ErrorApi as error:
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
                for item in error.errors:
                    ui.label(str(item)).classes("text-caption text-negative")
            return
        sesion.carrito.clear()
        ui.navigate.to(f"/pedidos/exitoso?id={pedido['id']}")

    with ui.row().classes("gap-2 my-2"):
        ui.button("Crear pedido", on_click=guardar)
        ui.button("Volver al carrito", on_click=lambda: ui.navigate.to("/carrito"))

    cargar_clientes()
    cargar_resumen()
