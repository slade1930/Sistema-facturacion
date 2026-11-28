"""Detalle y PDF de una factura propia; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.forms import boton_enlace, boton_orquidea, mostrar_error
from components.portal import montar_portal
from components.shared import estado_cargando, estado_vacio, ticket_factura
from pages.facturacion.detalle import COLUMNAS_LINEAS
from state import auth
from state.cliente_api import ErrorApi


def obtener(api: Any, factura_id: int) -> dict[str, Any]:
    return api.get(f"/api/v1/facturas/{factura_id}")


def descargar_pdf(api: Any, factura_id: int) -> bytes:
    return api.get(f"/api/v1/facturas/{factura_id}/pdf")


@ui.page("/portal/factura-detalle")
async def pagina_factura_detalle_empresa(factura_id: int | None = None) -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Detalle de mi factura", ruta_activa="/portal/facturas")

    mensajes = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")
    if factura_id is None:
        with resultado:
            estado_vacio(
                "Elige una factura desde tu historial.",
                "Solo puedes ver las facturas de tu empresa.",
            )
            boton_enlace("Ver mis facturas", "/portal/facturas")
        return

    with resultado:
        estado_cargando(4)

    async def descargar(factura: dict[str, Any]) -> None:
        mensajes.clear()
        try:
            contenido = await asyncio.to_thread(
                descargar_pdf, auth.cliente_portal(), int(factura["id"])
            )
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        ui.download(
            contenido,
            f"factura-{factura.get('numero_serie') or factura['id']}.pdf",
            media_type="application/pdf",
        )

    async def cargar() -> None:
        mensajes.clear()
        try:
            factura = await asyncio.to_thread(obtener, auth.cliente_portal(), factura_id)
        except ErrorApi as error:
            resultado.clear()
            mostrar_error(mensajes, error)
            with resultado:
                boton_enlace("Volver a mis facturas", "/portal/facturas")
            return
        except Exception:
            resultado.clear()
            with mensajes:
                ui.label("No pudimos cargar la factura.").classes("orq-error")
            return
        resultado.clear()
        with resultado:
            ticket_factura(factura, list(COLUMNAS_LINEAS))
            with ui.row().classes("orq-barra-acciones w-full"):
                boton_orquidea(
                    "Descargar PDF",
                    lambda: asyncio.create_task(descargar(factura)),
                    variante="secundario",
                )
                boton_enlace(
                    "Volver a mis facturas", "/portal/facturas", variante="texto"
                )

    asyncio.create_task(cargar())


__all__ = ["descargar_pdf", "obtener", "pagina_factura_detalle_empresa"]
