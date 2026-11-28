"""Panel de compras y recomendaciones de la empresa; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.dashboard import grafico, ranking, recomendaciones, tarjetas
from components.forms import mostrar_error
from components.portal import montar_portal
from components.shared import estado_cargando
from state import auth
from state.cliente_api import ErrorApi


def leer_items(respuesta: Any) -> list[dict[str, Any]]:
    if isinstance(respuesta, dict):
        return list(respuesta.get("items") or [])
    if isinstance(respuesta, list):
        return list(respuesta)
    return []


@ui.page("/portal/inicio")
async def pagina_inicio() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Mi portal", ruta_activa="/portal/inicio")

    mensajes = ui.column().classes("w-full")
    tarjetas_zone = ui.column().classes("w-full")
    grafico_zone = ui.column().classes("w-full")
    ranking_zone = ui.column().classes("w-full")
    sugerencias_zone = ui.column().classes("w-full")
    with tarjetas_zone:
        estado_cargando(3)

    async def cargar() -> None:
        api = auth.cliente_portal()
        _ = api.client  # una sola conexión httpx para las cuatro consultas
        try:
            historial, pedidos, productos, sugerencias = await asyncio.gather(
                asyncio.to_thread(
                    api.get, "/api/v1/historial", params={"limite": 20}
                ),
                asyncio.to_thread(api.get, "/api/v1/pedidos", params={"limite": 20}),
                asyncio.to_thread(api.get, "/api/v1/productos", params={"limite": 100}),
                asyncio.to_thread(
                    api.get, "/api/v1/ml/recomendaciones", params={"n": 5}
                ),
            )
        except ErrorApi as error:
            tarjetas_zone.clear()
            mostrar_error(mensajes, error)
            return
        except Exception:
            tarjetas_zone.clear()
            with mensajes:
                ui.label("No pudimos cargar tu panel. Inténtalo de nuevo.").classes(
                    "orq-error"
                )
            return

        facturas = leer_items(historial)
        lista_pedidos = leer_items(pedidos)
        nombres = {
            int(producto["id"]): str(producto.get("nombre") or "")
            for producto in productos
            if str(producto.get("id") or "").isdigit()
        }
        tarjetas_zone.clear()
        with tarjetas_zone:
            tarjetas(facturas, lista_pedidos)
            if facturas:
                ultima = facturas[0]
                ui.link(
                    f"Última factura: {ultima.get('numero_serie') or ''}",
                    f"/portal/factura-detalle?factura_id={ultima.get('id') or ''}",
                ).classes("orq-boton orq-boton--texto")
        with grafico_zone:
            ui.label("Actividad por fecha").classes("orq-tabla-titulo")
            grafico(facturas)
        with ranking_zone:
            ui.label("Lo que más pides").classes("orq-tabla-titulo")
            ranking(lista_pedidos)
        with sugerencias_zone:
            ui.label("Recomendaciones para tu empresa").classes("orq-tabla-titulo")
            recomendaciones(sugerencias, nombres)

    asyncio.create_task(cargar())


__all__ = ["leer_items", "pagina_inicio"]
