import os

from nicegui import ui

from components.layout import montar_layout
from pages.catalogo import carrito as _pagina_carrito
from pages.catalogo import catalogo as _pagina_catalogo
from pages.facturacion import detalle as _pagina_detalle
from pages.facturacion import historial as _pagina_historial
from pages.facturacion import nueva as _pagina_nueva
from pages.pedidos import convertir_a_factura as _pagina_convertir
from pages.pedidos import pedidos_pendientes as _pagina_pedidos
from pages.verificar import verificar as _pagina_verificar
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()


def probar_salud() -> None:
    try:
        respuesta = cliente.get("/health")
        ui.notify(f"Backend OK: {respuesta.get('status', 'sin estado')}")
    except ErrorApi as error:
        ui.notify(error.detail, type="negative")


@ui.page("/")
def inicio() -> None:
    montar_layout()
    with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-4"):
        ui.label("Facturación").classes("text-h4")
        ui.label("Interfaz NiceGUI conectada al backend por httpx.").classes("text-grey")
        with ui.card().classes("w-full"):
            ui.label("Backend").classes("text-subtitle1")
            ui.label(cliente.base_url)
            ui.button("Probar /health", on_click=probar_salud)
        with ui.row().classes("gap-2"):
            ui.button(
                "API docs",
                on_click=lambda: ui.navigate.to("http://localhost:8000/docs", new_tab=True),
            )


ui.run(
    host="0.0.0.0",
    port=int(os.getenv("UI_PORT", "8080")),
    title="Sistema de facturación",
)
