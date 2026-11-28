"""Recomendaciones de ML para la empresa; etapa B."""

from typing import Any

from nicegui import ui

from components.shared import estado_vacio


def recomendaciones(datos: dict[str, Any], nombres: dict[int, str]) -> None:
    """Muestra solo las sugerencias que el backend calculó para esta empresa."""
    resultado = datos.get("resultado") or {}
    items = resultado.get("recomendaciones") or []
    if not items:
        estado_vacio(
            "Todavía no hay recomendaciones.",
            "Vuelve a mirar después de comprar.",
        )
        return
    with ui.column().classes("w-full gap-1"):
        for item in items[:10]:
            producto_id = item.get("producto_id")
            try:
                clave = int(producto_id)
            except (TypeError, ValueError):
                continue
            nombre = nombres.get(clave, f"Producto #{clave}")
            fuente = str(item.get("fuente") or "").replace("_", " ")
            ui.link(
                f"{nombre} · {fuente}" if fuente else nombre,
                "/portal/catalogo",
            ).classes("orq-boton orq-boton--texto")
            puntaje = str(item.get("puntaje") or "")
            if puntaje:
                ui.label(f"Puntaje {puntaje}").classes("orq-ayuda")


__all__ = ["recomendaciones"]
