from typing import Any

from nicegui import ui

from components.forms import (
    boton_orquidea,
    campo_orquidea,
    confirmar_accion,
    mensaje_error,
    mostrar_error,
    notificar,
)
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


def descargar_pdf(cliente_api: ClienteApi, factura_id: int) -> bytes:
    """Descarga el documento sin exponer detalles técnicos."""
    return obtener_pdf(cliente_api, factura_id)


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/facturacion/detalle")
def pagina_detalle(factura_id: int | None = None) -> None:
    inicial = factura_id
    if inicial is None and sesion.ultima_factura:
        inicial = sesion.ultima_factura.get("id")

    texto_inicial = "" if inicial is None else str(inicial)
    factura_inicial: dict[str, Any] | None = None
    error_inicial: ErrorApi | None = None
    id_invalido = bool(texto_inicial) and not texto_inicial.isdigit()
    if texto_inicial.isdigit():
        try:
            factura_inicial = obtener(cliente, int(texto_inicial))
        except ErrorApi as error:
            error_inicial = error

    numero_inicial = _valor(factura_inicial or {}, "numero_serie")
    titulo = f"Factura {numero_inicial}" if numero_inicial else "Detalle de una factura"
    montar_layout(
        titulo,
        ruta_activa="/facturacion/detalle",
        migas="Facturas emitidas",
    )

    with ui.row().classes("w-full items-end gap-2"):
        entrada = campo_orquidea("Número de registro", value=texto_inicial)
        boton_orquidea("Cargar", lambda: cargar(), variante="secundario")
    mensajes = ui.column()
    resultado = ui.column().classes("w-full")
    actual: dict[str, Any] = {"factura": None}

    def pintar(factura: dict[str, Any]) -> None:
        actual["factura"] = factura
        sesion.ultima_factura = factura
        resultado.clear()
        with resultado:
            with ui.element("div").classes("orq-dos-columnas w-full"):
                ticket_factura(factura, list(COLUMNAS_LINEAS))
                with ui.column().classes("w-full gap-2"):
                    ui.label("Acciones").classes("orq-tabla-titulo")
                    with ui.row().classes("orq-ticket-acciones w-full"):
                        boton_orquidea("Anular", pedir_anulacion, variante="peligro")
                        boton_orquidea(
                            "Duplicar", duplicar_actual, variante="secundario"
                        )
                        boton_orquidea(
                            "Descargar PDF", descargar, variante="secundario"
                        )

    def cargar() -> None:
        mensajes.clear()
        texto = (entrada.value or "").strip()
        if not texto.isdigit():
            with mensajes:
                mensaje_error("Ingresa un número de registro válido.")
            return
        try:
            factura = obtener(cliente, int(texto))
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        pintar(factura)

    def anular_actual() -> None:
        factura = actual["factura"]
        if factura is None:
            return
        try:
            actualizada = anular(cliente, int(factura["id"]))
        except ErrorApi as error:
            mensajes.clear()
            mostrar_error(mensajes, error)
            return
        pintar(actualizada)
        notificar("Factura anulada. Ya no se puede emitir.")

    def pedir_anulacion() -> None:
        confirmar_accion(
            "Anular factura",
            "La factura dejará de estar vigente. Esta acción no se puede deshacer.",
            anular_actual,
            etiqueta_confirmar="Anular",
            peligro=True,
        )

    def duplicar_actual() -> None:
        factura = actual["factura"]
        if factura is None:
            return
        try:
            nueva = duplicar(cliente, int(factura["id"]))
        except ErrorApi as error:
            mensajes.clear()
            mostrar_error(mensajes, error)
            return
        pintar(nueva)
        notificar(f"Duplicada como {nueva['numero_serie']}.")

    def descargar() -> None:
        factura = actual["factura"]
        if factura is None:
            return
        try:
            contenido = descargar_pdf(cliente, int(factura["id"]))
        except ErrorApi as error:
            mensajes.clear()
            mostrar_error(mensajes, error)
            return
        ui.download(
            contenido,
            f"factura-{factura['numero_serie']}.pdf",
            media_type="application/pdf",
        )

    if error_inicial is not None:
        mostrar_error(mensajes, error_inicial)
    elif id_invalido:
        with mensajes:
            mensaje_error("Ingresa un número de registro válido.")
    elif factura_inicial is not None:
        pintar(factura_inicial)
