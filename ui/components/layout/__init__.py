from nicegui import ui

ENLACES = (
    ("Inicio", "/"),
    ("Nueva factura", "/facturacion/nueva"),
    ("Historial", "/facturacion/historial"),
    ("Catálogo", "/catalogo"),
    ("Pedidos", "/pedidos/por-facturar"),
    ("Verificar", "/verificar"),
)


def montar_layout(titulo: str = "Sistema de facturación") -> None:
    with ui.header().classes("items-center justify-between bg-primary text-white"):
        ui.label(titulo).classes("text-h6")
        with ui.row().classes("gap-2"):
            for texto, ruta in ENLACES:
                ui.link(texto, ruta).classes("text-white")
