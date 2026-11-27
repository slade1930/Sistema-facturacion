from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()

ENVASES = {
    "caja": "Caja",
    "media_caja": "Media caja",
    "unidad": "Unidad",
}


def lineas_para_calculo(carrito: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "producto_id": item["producto_id"],
            "tipo_empaque": item["tipo_empaque"],
            "cantidad": str(item["cantidad"]),
        }
        for item in carrito
    ]


def calcular(cliente_api: ClienteApi, carrito: list[dict[str, Any]]) -> dict[str, Any]:
    return cliente_api.post(
        "/api/v1/carrito/calcular",
        json={"lineas": lineas_para_calculo(carrito)},
    )


def leer_carrito(carrito: list[dict[str, Any]]) -> list[dict[str, Any]]:
    leido = []
    for item in carrito:
        envase = item.get("_envase")
        cantidad = item.get("_cantidad")
        leido.append(
            {
                "producto_id": item["producto_id"],
                "nombre": item["nombre"],
                "tipo_empaque": str(envase.value or "caja") if envase else item["tipo_empaque"],
                "cantidad": float(cantidad.value or 0) if cantidad else float(item["cantidad"]),
            }
        )
    return leido


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/carrito")
def pagina_carrito() -> None:
    montar_layout("Carrito")

    mensajes = ui.column()
    lista = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")

    def quitar(item: dict[str, Any]) -> None:
        if item in sesion.carrito:
            sesion.carrito.remove(item)
        pintar()

    def pintar() -> None:
        lista.clear()
        if not sesion.carrito:
            with lista:
                ui.label("El carrito está vacío.").classes("text-grey")
            return
        for item in sesion.carrito:
            with lista:
                with ui.card().classes("w-full"):
                    ui.label(_valor(item, "nombre")).classes("text-h6")
                    with ui.row().classes("w-full gap-2 items-center"):
                        item["_envase"] = ui.select(
                            ENVASES,
                            label="Presentación",
                            value=item["tipo_empaque"],
                        )
                        item["_cantidad"] = ui.number(
                            "Cantidad",
                            value=float(item["cantidad"]),
                            min=0.01,
                            precision=2,
                        )
                        ui.button("Quitar", on_click=lambda i=item: quitar(i))

    def calcular_totales() -> None:
        mensajes.clear()
        resultado.clear()
        if not sesion.carrito:
            with mensajes:
                ui.label("No hay productos en el carrito.").classes("text-negative")
            return
        leido = leer_carrito(sesion.carrito)
        for item, valores in zip(sesion.carrito, leido):
            item["tipo_empaque"] = valores["tipo_empaque"]
            item["cantidad"] = valores["cantidad"]
        try:
            datos = calcular(cliente, sesion.carrito)
        except ErrorApi as error:
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            return
        with resultado:
            with ui.card().classes("w-full"):
                ui.label("Totales estimados").classes("text-h6")
                campos = (
                    ("Subtotal", "subtotal"),
                    ("Descuento", "descuento_total"),
                    ("Base gravada", "base_gravada"),
                    ("Base exenta", "base_exenta"),
                    ("ITBMS", "itbms"),
                    ("Total", "total"),
                )
                for etiqueta, campo in campos:
                    with ui.row().classes("w-full justify-between"):
                        ui.label(f"{etiqueta}:").classes("text-grey")
                        ui.label(_valor(datos, campo))

    with ui.row().classes("gap-2 my-2"):
        ui.button("Calcular", on_click=calcular_totales)
        ui.button("Vaciar", on_click=lambda: vaciar())

    def vaciar() -> None:
        sesion.carrito.clear()
        mensajes.clear()
        resultado.clear()
        pintar()

    pintar()
