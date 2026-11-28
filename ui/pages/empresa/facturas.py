"""Facturas propias de la empresa; etapa B."""

import asyncio
from typing import Any

from nicegui import ui

from components.forms import mostrar_error
from components.portal import montar_portal
from components.shared import estado_cargando, estado_vacio, tabla_orquidea
from state import auth
from state.cliente_api import ErrorApi

COLUMNAS = [
    {"name": "numero_serie", "label": "Número", "field": "numero_serie", "align": "left"},
    {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "left"},
    {"name": "cliente_nombre", "label": "Empresa", "field": "cliente_nombre", "align": "left"},
    {"name": "total", "label": "Total", "field": "total", "align": "right"},
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
    {"name": "accion", "label": "Acción", "field": "accion", "align": "left"},
]

SELLO_FILA = """
<div>
  <span class="orq-sello orq-sello--neutro">{{ props.value }}</span>
</div>
"""

ACCION_FILA = """
<div>
  <a class="orq-boton orq-boton--texto"
     href="/portal/factura-detalle?factura_id={{ props.value }}">Ver</a>
</div>
"""


def consultar(api: Any, limite: int = 50) -> dict[str, Any]:
    return api.get("/api/v1/historial", params={"limite": limite})


@ui.page("/portal/facturas")
async def pagina_facturas_empresa() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Mis facturas", ruta_activa="/portal/facturas")

    mensajes = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")
    with resultado:
        estado_cargando(5)

    def pintar(facturas: list[dict[str, Any]]) -> None:
        resultado.clear()
        if not facturas:
            with resultado:
                estado_vacio(
                    "Todavía no tienes facturas.",
                    "Cuando compres, aparecerán acá.",
                )
            return
        filas = [
            {
                **{
                    clave: factura.get(clave)
                    for clave in (
                        "id",
                        "numero_serie",
                        "fecha",
                        "cliente_nombre",
                        "total",
                        "estado",
                    )
                },
                "accion": factura.get("id"),
            }
            for factura in facturas
        ]
        with resultado:
            tablero = tabla_orquidea(COLUMNAS, filas, row_key="id")
            tablero.add_slot("body-cell-estado", SELLO_FILA)
            tablero.add_slot("body-cell-accion", ACCION_FILA)

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
                ui.label("No pudimos cargar tus facturas.").classes("orq-error")
            return
        pintar(list(datos.get("items") or []))

    asyncio.create_task(cargar())


__all__ = ["consultar", "pagina_facturas_empresa"]
