"""Confirmación de la compra con su factura; etapa B."""

from nicegui import ui

from components.forms import boton_enlace
from components.portal import montar_portal
from components.shared import estado_vacio, total_animado
from state import auth


@ui.page("/portal/compra-exitosa")
async def pagina_compra_exitosa(
    factura_id: int | None = None,
    pedido_id: int | None = None,
    numero_serie: str | None = None,
    total: str | None = None,
    reutilizada: str | None = None,
) -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Compra confirmada", ruta_activa="/portal/facturas")

    if factura_id is None:
        estado_vacio(
            "No hay una compra reciente para mostrar.",
            "Vuelve al catálogo cuando quieras comprar.",
        )
        with ui.row().classes("orq-barra-acciones w-full"):
            boton_enlace("Ver catálogo", "/portal/catalogo")
        return

    with ui.element("section").classes("orq-ticket w-full"):
        ui.label("Tu compra quedó registrada").classes("orq-ticket-titulo")
        if str(reutilizada) in ("1", "true", "True"):
            ui.label(
                "Esta compra ya se había confirmado; mostramos la misma factura."
            ).classes("orq-bloque-ayuda")
        for etiqueta, valor in (
            ("Factura", numero_serie or "—"),
            ("Pedido", f"#{pedido_id}" if pedido_id else "—"),
        ):
            with ui.element("div").classes("orq-dato"):
                ui.label(etiqueta).classes("orq-dato-etiqueta")
                ui.label(str(valor)).classes("orq-dato-valor")
        total_animado(str(total or "0.00"))
    with ui.row().classes("orq-barra-acciones w-full"):
        boton_enlace(
            "Ver factura", f"/portal/factura-detalle?factura_id={factura_id}"
        )
        boton_enlace("Ver mis facturas", "/portal/facturas", variante="secundario")
        boton_enlace("Seguir comprando", "/portal/catalogo", variante="secundario")


__all__ = ["pagina_compra_exitosa"]
