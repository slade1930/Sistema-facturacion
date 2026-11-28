"""Carrito y compra con factura automática de la empresa; etapa B."""

import asyncio
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from nicegui import ui

from components.forms import (
    boton_enlace,
    boton_orquidea,
    confirmar_accion,
    mensaje_error,
    mostrar_error,
    notificar,
    numero_orquidea,
    selector_orquidea,
)
from components.portal import montar_portal
from components.shared import estado_cargando, estado_vacio, ticket_resumen
from pages.catalogo.carrito import leer_carrito, lineas_para_calculo, opciones_empaque
from state import auth
from state.cliente_api import ErrorApi
from state.sesion import actualizar_contador, sesion


def calcular(api: Any, carrito: list[dict[str, Any]]) -> dict[str, Any]:
    return api.post(
        "/api/v1/carrito/calcular", json={"lineas": lineas_para_calculo(carrito)}
    )


def comprar(
    api: Any, lineas: list[dict[str, Any]], clave: str
) -> dict[str, Any]:
    return api.post(
        "/api/v1/compras",
        json={"lineas": lineas, "clave_idempotencia": clave},
    )


@ui.page("/portal/carrito")
async def pagina_carrito_empresa() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Mi carrito", ruta_activa="/portal/carrito")

    carrito = sesion.carrito
    mensajes = ui.column().classes("w-full gap-1")
    with ui.element("div").classes("orq-dos-columnas w-full"):
        with ui.element("section").classes("w-full") as lista:
            pass
        with ui.element("section").classes("w-full") as resultado:
            pass

    calculo: dict[str, Any] = {}
    controles: dict[int, dict[str, Any]] = {}
    clave_compra: dict[str, str | None] = {"valor": None}

    def clave_actual() -> str:
        if clave_compra["valor"] is None:
            clave_compra["valor"] = uuid4().hex
        return clave_compra["valor"]

    def pintar() -> None:
        lista.clear()
        controles.clear()
        if not carrito:
            with lista:
                estado_vacio(
                    "Tu carrito está vacío.",
                    "Añade productos de tu sector para empezar.",
                )
                boton_enlace("Ver catálogo", "/portal/catalogo")
            return
        for indice, item in enumerate(carrito):
            with lista:
                with ui.element("div").classes(
                    "orq-linea orq-linea-carrito w-full items-center"
                ):
                    ui.label(str(item.get("nombre") or "")).classes(
                        "orq-entrada-titulo"
                    )
                    envase = selector_orquidea(
                        "Presentación",
                        opciones_empaque(item),
                        value=item["tipo_empaque"],
                        buscar=False,
                    )
                    cantidad = numero_orquidea(
                        "Cantidad",
                        value=float(item["cantidad"]),
                        min=0.01,
                        precision=2,
                    )
                    controles[indice] = {"envase": envase, "cantidad": cantidad}

    async def calcular_totales() -> bool:
        mensajes.clear()
        resultado.clear()
        calculo.clear()
        if not carrito:
            return False
        with resultado:
            estado_cargando(3)
        try:
            datos = await asyncio.to_thread(calcular, auth.cliente_portal(), carrito)
        except ErrorApi as error:
            resultado.clear()
            mostrar_error(mensajes, error)
            return False
        except Exception:
            resultado.clear()
            with mensajes:
                mensaje_error("No pudimos calcular el carrito. Inténtalo de nuevo.")
            return False
        leido = leer_carrito(carrito, controles)
        for item, valores in zip(carrito, leido):
            item["tipo_empaque"] = valores["tipo_empaque"]
            item["cantidad"] = valores["cantidad"]
        calculo.update(datos)
        lineas = [
            {
                "descripcion": (
                    f"{linea.get('descripcion') or ''} · "
                    f"{linea.get('tipo_empaque') or ''} × {linea.get('cantidad') or ''}"
                ),
                "importe": str(linea.get("subtotal") or "0.00"),
            }
            for linea in datos.get("lineas") or []
        ]
        resultado.clear()
        with resultado:
            ticket_resumen(datos, lineas, titulo="Totales de tu compra")
        return True

    async def confirmar() -> None:
        if not carrito:
            notificar("El carrito está vacío.", tipo="warning")
            return
        mensajes.clear()
        if not calculo and not await calcular_totales():
            return
        leido = leer_carrito(carrito, controles)
        if any(float(linea["cantidad"]) <= 0 for linea in leido):
            with mensajes:
                ui.label("Elige una cantidad mayor a cero.").classes("orq-error")
            return
        lineas = [
            {
                "producto_id": item["producto_id"],
                "tipo_empaque": item["tipo_empaque"],
                "cantidad": str(item["cantidad"]),
            }
            for item in carrito
        ]
        clave = clave_actual()
        try:
            respuesta = await asyncio.to_thread(comprar, auth.cliente_portal(), lineas, clave)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            with mensajes:
                mensaje_error("No pudimos completar la compra. Inténtalo de nuevo.")
            return
        carrito.clear()
        sesion.carrito = carrito
        clave_compra["valor"] = None
        actualizar_contador(carrito)
        with mensajes:
            ui.label("Compra confirmada. Tu factura ya está lista.").classes(
                "orq-aviso-pedidos"
            )
        consulta = urlencode(
            {
                "factura_id": respuesta.get("factura_id") or "",
                "pedido_id": respuesta.get("pedido_id") or "",
                "numero_serie": respuesta.get("numero_serie") or "",
                "total": respuesta.get("total") or "",
                "reutilizada": "1" if respuesta.get("reutilizada") else "0",
            }
        )
        ui.navigate.to(f"/portal/compra-exitosa?{consulta}")

    def vaciar() -> None:
        carrito.clear()
        sesion.carrito = carrito
        clave_compra["valor"] = None
        mensajes.clear()
        resultado.clear()
        calculo.clear()
        actualizar_contador(carrito)
        notificar("Carrito vacío.")
        pintar()

    def pedir_vaciado() -> None:
        if not carrito:
            return
        confirmar_accion(
            "Vaciar el carrito",
            "Se quitarán todos los productos. ¿Continuar?",
            vaciar,
            etiqueta_confirmar="Vaciar",
        )

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Confirmar compra", lambda: asyncio.create_task(confirmar()))
        boton_orquidea("Vaciar", pedir_vaciado, variante="peligro")
        boton_enlace("Seguir comprando", "/portal/catalogo", variante="secundario")

    pintar()
    if carrito:
        asyncio.create_task(calcular_totales())


__all__ = ["calcular", "comprar", "pagina_carrito_empresa"]
