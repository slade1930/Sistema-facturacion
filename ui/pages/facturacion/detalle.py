from typing import Any

from nicegui import ui

from components.forms import boton_orquidea, campo_orquidea, mensaje_error, notificar
from components.layout import montar_layout
from components.shared import ticket_factura
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
    montar_layout("Detalle de factura", ruta_activa="/facturacion/historial")

    inicial = factura_id
    if inicial is None and sesion.ultima_factura:
        inicial = sesion.ultima_factura.get("id")

    with ui.row().classes("w-full items-end gap-2"):
        entrada = campo_orquidea(
            "ID de factura", value=str(inicial) if inicial is not None else ""
        )
        boton_orquidea("Cargar", lambda: cargar(), variante="secundario")
    mensajes = ui.column()
    resultado = ui.column().classes("w-full")
    actual: dict[str, Any] = {"factura": None}

    def mostrar_error(error: ErrorApi) -> None:
        mensajes.clear()
        with mensajes:
            mensaje_error(f"{error.code}: {error.detail}")
            for item in error.errors:
                ubicacion = ".".join(str(parte) for parte in item.get("loc", []))
                texto = item.get("msg") or item.get("detail") or "Valor inválido."
                mensaje_error(f"{ubicacion}: {texto}" if ubicacion else texto)

    def pintar(factura: dict[str, Any]) -> None:
        actual["factura"] = factura
        sesion.ultima_factura = factura
        resultado.clear()
        with resultado:
            ticket_factura(factura, list(COLUMNAS_LINEAS))
            with ui.row().classes("orq-ticket-acciones"):
                boton_orquidea("Anular", lambda: anular_actual(), variante="peligro")
                boton_orquidea(
                    "Duplicar", lambda: duplicar_actual(), variante="secundario"
                )
                boton_orquidea(
                    "Descargar PDF", lambda: descargar(), variante="secundario"
                )

    def cargar() -> None:
        mensajes.clear()
        texto = (entrada.value or "").strip()
        if not texto.isdigit():
            with mensajes:
                mensaje_error("Ingresá un ID numérico de factura.")
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
        notificar("Factura anulada. Ya no se puede emitir.")

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
        notificar(f"Duplicada como {nueva['numero_serie']}.")

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
