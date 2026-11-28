"""Ranking de lo que más pide la empresa; etapa B."""

from typing import Any

from nicegui import ui

from components.shared import estado_vacio

ENVASES = {"caja": "Caja", "media_caja": "Media caja", "unidad": "Unidad"}


def ranking(pedidos: list[dict[str, Any]], *, limite: int = 5) -> None:
    """Cuenta líneas de los pedidos propios que devolvió el backend."""
    conteo: dict[tuple[Any, str], int] = {}
    for pedido in pedidos:
        for linea in pedido.get("lineas") or []:
            clave = (linea.get("producto_id"), str(linea.get("tipo_empaque") or "caja"))
            conteo[clave] = conteo.get(clave, 0) + 1
    if not conteo:
        estado_vacio("Todavía no hay productos pedidos para mostrar.")
        return
    mas_usados = sorted(conteo.items(), key=lambda item: (-item[1], str(item[0])))[:limite]
    with ui.column().classes("w-full gap-1"):
        for (producto_id, empaque), veces in mas_usados:
            with ui.row().classes("w-full justify-between"):
                ui.label(
                    f"Producto #{producto_id} · {ENVASES.get(empaque, empaque)}"
                ).classes("orq-resumen")
                ui.label(f"{veces} pedidos").classes("orq-resumen")


__all__ = ["ranking"]
