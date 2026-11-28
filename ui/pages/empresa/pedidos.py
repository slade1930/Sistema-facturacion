"""Pedidos propios de la empresa; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.forms import mostrar_error
from components.portal import montar_portal
from components.shared import estado_cargando, estado_vacio, tabla_orquidea
from state import auth
from state.cliente_api import ErrorApi

COLUMNAS = [
    {"name": "id", "label": "Pedido", "field": "id", "align": "left"},
    {"name": "fecha_creacion", "label": "Fecha", "field": "fecha_creacion", "align": "left"},
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
    {"name": "total_estimado", "label": "Total", "field": "total_estimado", "align": "right"},
    {"name": "factura", "label": "Factura", "field": "factura", "align": "left"},
]


def consultar(api: Any, limite: int = 50) -> dict[str, Any]:
    return api.get("/api/v1/pedidos", params={"limite": limite})


@ui.page("/portal/pedidos")
async def pagina_pedidos_empresa() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Mis pedidos", ruta_activa="/portal/pedidos")

    mensajes = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")
    with resultado:
        estado_cargando(5)

    def pintar(pedidos: list[dict[str, Any]]) -> None:
        resultado.clear()
        if not pedidos:
            with resultado:
                estado_vacio(
                    "Todavía no tienes pedidos.",
                    "Cuando compres, aparecerán acá.",
                )
            return
        filas = []
        for pedido in pedidos:
            fila = dict(pedido)
            fila["id"] = f"#{pedido.get('id')}"
            fila["factura"] = (
                f"#{pedido['factura_generada_id']}"
                if pedido.get("factura_generada_id")
                else "—"
            )
            filas.append(fila)
        with resultado:
            tabla_orquidea(COLUMNAS, filas, row_key="id")

    async def cargar() -> None:
        mensajes.clear()
        try:
            datos = await asyncio.to_thread(consultar, auth.cliente_portal())
        except ErrorApi as error:
            resultado.clear()
            mostrar_error(mensajes, error)
            return
        except Exception:
            resultado.clear()
            with mensajes:
                ui.label("No pudimos cargar tus pedidos.").classes("orq-error")
            return
        pintar(list(datos.get("items") or []))

    asyncio.create_task(cargar())


__all__ = ["consultar", "pagina_pedidos_empresa"]
