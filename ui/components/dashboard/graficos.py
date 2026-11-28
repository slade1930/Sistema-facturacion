"""Gráfico sencillo de actividad reciente; etapa B."""

from typing import Any

from nicegui import ui

from components.shared import estado_vacio


def _ancho(valor: float, mayor: float) -> int:
    if mayor <= 0:
        return 0
    return max(4, min(100, int(round(valor / mayor * 100))))


def grafico(facturas: list[dict[str, Any]]) -> None:
    """Barras por fecha, sin librerías nuevas y sin cálculos de facturación."""
    if not facturas:
        estado_vacio("Todavía no hay facturas para graficar.")
        return
    por_fecha: dict[str, float] = {}
    for factura in facturas:
        fecha = str(factura.get("fecha") or "Sin fecha")
        try:
            importe = float(factura.get("total") or 0)
        except (TypeError, ValueError):
            importe = 0.0
        por_fecha[fecha] = por_fecha.get(fecha, 0.0) + importe
    mayor = max(por_fecha.values(), default=0.0)
    with ui.column().classes("w-full gap-2"):
        for fecha, importe in list(por_fecha.items())[:8]:
            with ui.element("div").classes("w-full"):
                ui.label(f"{fecha} · {importe:.2f}").classes("orq-bloque-ayuda")
                ui.html(
                    '<div class="w-full" style="background:#eee;border-radius:8px;height:8px">'
                    '<div style="height:8px;border-radius:8px;background:#6C2BD9;width:'
                    + str(_ancho(importe, mayor))
                    + '%"></div></div>',
                    sanitize=False,
                )


__all__ = ["grafico"]
