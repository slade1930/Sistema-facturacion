from typing import Any

from nicegui import ui

from components.forms import (
    boton_enlace,
    boton_orquidea,
    confirmar_accion,
    mostrar_error,
    notificar,
    numero_orquidea,
    selector_orquidea,
)
from components.layout import montar_layout
from components.shared import estado_vacio, ticket_resumen
from state.cliente_api import ClienteApi
from state.sesion import sesion

cliente = ClienteApi()

ENVASES = {
    "caja": "Caja",
    "media_caja": "Media caja",
    "unidad": "Unidad",
}

_ESTILO_LINEA = (
    "grid-template-columns: minmax(160px, 2fr) minmax(140px, 1fr) "
    "minmax(110px, 1fr) 44px"
)


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
    montar_layout("Tu carrito", ruta_activa="/carrito", migas="Productos")

    mensajes = ui.column().classes("w-full")
    with ui.element("div").classes("orq-dos-columnas w-full"):
        with ui.element("section").classes("w-full") as lista:
            pass
        with ui.element("section").classes("w-full") as resultado:
            pass

    def descartar_totales() -> None:
        resultado.clear()

    def quitar(item: dict[str, Any]) -> None:
        if item in sesion.carrito:
            sesion.carrito.remove(item)
        descartar_totales()
        notificar("Producto quitado del carrito.")
        pintar()

    def pintar() -> None:
        lista.clear()
        if not sesion.carrito:
            with lista:
                estado_vacio(
                    "El carrito está vacío.",
                    "Cuando agregues productos, aparecen acá.",
                )
            return

        with lista:
            with ui.element("div").classes(
                "orq-linea orq-linea-cabecera w-full"
            ).style(_ESTILO_LINEA):
                ui.label("Producto")
                ui.label("Presentación")
                ui.label("Cantidad")
                ui.label("")

        for item in sesion.carrito:
            with lista:
                with ui.element("div").classes("orq-linea w-full items-center").style(
                    _ESTILO_LINEA
                ):
                    ui.label(_valor(item, "nombre")).classes("orq-entrada-titulo")
                    item["_envase"] = selector_orquidea(
                        "Presentación",
                        ENVASES,
                        value=item["tipo_empaque"],
                        buscar=False,
                        on_value_change=descartar_totales,
                    )
                    item["_cantidad"] = numero_orquidea(
                        "Cantidad",
                        value=float(item["cantidad"]),
                        min=0.01,
                        precision=2,
                        on_value_change=descartar_totales,
                    )
                    boton_orquidea(
                        "Quitar",
                        lambda i=item: quitar(i),
                        variante="secundario",
                    )

    def calcular_totales() -> None:
        mensajes.clear()
        resultado.clear()
        if not sesion.carrito:
            return

        leido = leer_carrito(sesion.carrito)
        if any(float(linea["cantidad"]) <= 0 for linea in leido):
            notificar("Revisá las cantidades antes de calcular.", tipo="warning")
            return

        for item, valores in zip(sesion.carrito, leido):
            item["tipo_empaque"] = valores["tipo_empaque"]
            item["cantidad"] = valores["cantidad"]

        try:
            datos = calcular(cliente, sesion.carrito)
        except Exception as error:
            mostrar_error(mensajes, error)
            return

        lineas = [
            {
                "descripcion": (
                    f"{_valor(linea, 'descripcion')} · "
                    f"{ENVASES.get(linea.get('tipo_empaque'), 'Presentación')} × "
                    f"{_valor(linea, 'cantidad')}"
                ),
                "importe": _valor(linea, "subtotal"),
            }
            for linea in datos.get("lineas") or []
        ]
        with resultado:
            ticket_resumen(datos, lineas, titulo="Totales del carrito")

    def vaciar() -> None:
        sesion.carrito.clear()
        mensajes.clear()
        resultado.clear()
        notificar("Carrito vacío.")
        pintar()

    def pedir_vaciado() -> None:
        if not sesion.carrito:
            return
        confirmar_accion(
            "Vaciar el carrito",
            "Se van a quitar todos los productos. ¿Continuar?",
            vaciar,
            etiqueta_confirmar="Vaciar",
        )

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Calcular", calcular_totales)
        boton_orquidea("Vaciar", pedir_vaciado, variante="peligro")
        boton_enlace("Seguir comprando", "/catalogo", variante="secundario")

    pintar()
