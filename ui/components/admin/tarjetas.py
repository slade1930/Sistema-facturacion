"""Tarjetas del resumen global; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin.formato import dinero, texto

TARJETAS = (
    ("Empresas", "empresas_total", ""),
    ("Empresas activas", "empresas_activas", ""),
    ("Empresas en línea", "empresas_en_linea", ""),
    ("Pedidos por facturar", "pedidos_por_facturar", "orq-admin-tarjeta--alerta"),
    ("Facturas en revisión", "facturas_en_revision", "orq-admin-tarjeta--alerta"),
    ("Productos bajo mínimo", "productos_bajo_minimo", "orq-admin-tarjeta--alerta"),
    ("Ingresos del período", "ingresos_periodo", "orq-admin-tarjeta--dinero"),
    ("Facturas del período", "facturas_periodo", ""),
)


def tarjetas_admin(resumen: dict[str, Any]) -> None:
    """Muestra únicamente las cifras que devolvió el backend."""
    with ui.element("div").classes("orq-admin-tarjetas"):
        for etiqueta, clave, clase in TARJETAS:
            valor = (
                dinero(resumen.get(clave))
                if clave == "ingresos_periodo"
                else texto(resumen.get(clave))
            )
            with ui.element("article").classes(f"orq-admin-tarjeta {clase}".strip()):
                ui.label(etiqueta).classes("orq-admin-tarjeta-etiqueta")
                ui.label(valor).classes("orq-admin-tarjeta-valor orq-total")


__all__ = ["tarjetas_admin"]
