"""Tarjetas de resumen del panel de la empresa; etapa B."""

from decimal import Decimal, InvalidOperation
from typing import Any

from nicegui import ui

from components.shared import total_animado


def _numero(valor: Any) -> Decimal:
    try:
        return Decimal(str(valor or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def tarjetas(facturas: list[dict[str, Any]], pedidos: list[dict[str, Any]]) -> None:
    """Muestra tres cifras simples calculadas con lo que devolvió el backend."""
    total = sum(
        (_numero(factura.get("total")) for factura in facturas), Decimal("0")
    )
    pendientes = sum(
        1
        for pedido in pedidos
        if str(pedido.get("estado") or "") in {"pendiente", "en_proceso"}
    )
    datos = (
        ("Facturas", str(len(facturas))),
        ("Pedidos", str(len(pedidos))),
        ("Por facturar", str(pendientes)),
    )
    with ui.row().classes("w-full gap-3"):
        for titulo, valor in datos:
            with ui.element("article").classes("orq-entrada w-full").style(
                "box-shadow: none !important"
            ):
                ui.label(titulo).classes("orq-bloque-ayuda")
                ui.label(valor).classes("orq-entrada-numero orq-total")
    ui.label("Total facturado").classes("orq-bloque-ayuda")
    total_animado(f"{_numero(total):.2f}")


__all__ = ["tarjetas"]
