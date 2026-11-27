from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()

COLUMNAS_LINEAS = (
    {"name": "orden", "label": "#", "field": "orden", "align": "left"},
    {"name": "descripcion", "label": "Descripción", "field": "descripcion", "align": "left"},
    {"name": "cantidad", "label": "Cantidad", "field": "cantidad", "align": "right"},
    {"name": "precio_unitario", "label": "P. unitario", "field": "precio_unitario", "align": "right"},
    {"name": "descuento_pct", "label": "Desc. %", "field": "descuento_pct", "align": "right"},
    {"name": "monto", "label": "Monto", "field": "monto", "align": "right"},
)


def obtener(cliente_api: ClienteApi, factura_id: int) -> dict[str, Any]:
    return cliente_api.get(f"/api/v1/facturas/{factura_id}")


def anular(cliente_api: ClienteApi, factura_id: int) -> dict[str, Any]:
    return cliente_api.post(f"/api/v1/facturas/{factura_id}/anular")


def duplicar(cliente_api: ClienteApi, factura_id: int) -> dict[str, Any]:
    return cliente_api.post(f"/api/v1/facturas/{factura_id}/duplicar")


def obtener_pdf(cliente_api: ClienteApi, factura_id: int) -> bytes:
    return cliente_api.get(f"/api/v1/facturas/{factura_id}/pdf")


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/facturacion/detalle")
def pagina_detalle(factura_id: int | None = None) -> None:
    montar_layout("Detalle de factura")

    inicial = factura_id
    if inicial is None and sesion.ultima_factura:
        inicial = sesion.ultima_factura.get("id")

    entrada = ui.input(
        "ID de factura", value=str(inicial) if inicial is not None else ""
    )
    ui.button("Cargar", on_click=lambda: cargar()).classes("mt-2")
    mensajes = ui.column()
    resultado = ui.column().classes("w-full")
    actual: dict[str, Any] = {"factura": None}

    def mostrar_error(error: ErrorApi) -> None:
        mensajes.clear()
        with mensajes:
            ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            for item in error.errors:
                ui.label(str(item)).classes("text-caption text-negative")

    def pintar(factura: dict[str, Any]) -> None:
        actual["factura"] = factura
        sesion.ultima_factura = factura
        resultado.clear()
        with resultado:
            with ui.card().classes("w-full"):
                ui.label(
                    f"{_valor(factura, 'numero_serie')} · {_valor(factura, 'estado')}"
                ).classes("text-h6")
                campos = (
                    ("Cliente", "cliente_nombre"),
                    ("RUC", "cliente_ruc"),
                    ("Fecha", "fecha"),
                    ("Condición", "condicion_pago"),
                    ("Subtotal", "subtotal"),
                    ("Descuento", "descuento_total"),
                    ("Base gravada", "base_gravada"),
                    ("Base exenta", "base_exenta"),
                    ("ITBMS", "itbms"),
                    ("Portes", "portes"),
                    ("Total", "total"),
                    ("Código de verificación", "codigo_verificacion"),
                    ("Orden de compra", "orden_compra"),
                    ("Notas", "notas"),
                )
                for etiqueta, campo in campos:
                    with ui.row().classes("w-full justify-between"):
                        ui.label(f"{etiqueta}:").classes("text-grey")
                        ui.label(_valor(factura, campo))

                ui.table(
                    columns=list(COLUMNAS_LINEAS),
                    rows=list(factura.get("lineas", [])),
                    row_key="id",
                ).classes("w-full")

                with ui.row().classes("gap-2 mt-2"):
                    ui.button("Anular", on_click=lambda: anular_actual())
                    ui.button("Duplicar", on_click=lambda: duplicar_actual())
                    ui.button("Descargar PDF", on_click=lambda: descargar())

    def cargar() -> None:
        mensajes.clear()
        texto = (entrada.value or "").strip()
        if not texto.isdigit():
            with mensajes:
                ui.label("Ingresá un ID numérico de factura.").classes("text-negative")
            return
        try:
            factura = obtener(cliente, int(texto))
        except ErrorApi as error:
            mostrar_error(error)
            return
        pintar(factura)

    def anular_actual() -> None:
        factura = actual["factura"]
        if factura is None:
            return
        try:
            actualizada = anular(cliente, int(factura["id"]))
        except ErrorApi as error:
            mostrar_error(error)
            return
        pintar(actualizada)
        ui.notify("Factura anulada.", type="positive")

    def duplicar_actual() -> None:
        factura = actual["factura"]
        if factura is None:
            return
        try:
            nueva = duplicar(cliente, int(factura["id"]))
        except ErrorApi as error:
            mostrar_error(error)
            return
        pintar(nueva)
        ui.notify(f"Duplicada como {nueva['numero_serie']}.", type="positive")

    def descargar() -> None:
        factura = actual["factura"]
        if factura is None:
            return
        try:
            contenido = obtener_pdf(cliente, int(factura["id"]))
        except ErrorApi as error:
            mostrar_error(error)
            return
        ui.download(
            contenido,
            f"factura-{factura['numero_serie']}.pdf",
            media_type="application/pdf",
        )

    if inicial is not None:
        cargar()
