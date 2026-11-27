from typing import Any

from nicegui import ui

from components.forms import boton_orquidea, campo_orquidea, mensaje_error, notificar
from components.layout import montar_layout
from components.shared import sello_emitir, sello_estado, total_animado
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()

CONDICIONES = {"contado": "Contado", "credito": "Crédito"}
COBRAR_POR = {"unidad": "Unidad", "caja": "Caja"}


def _decimal(valor: Any) -> str | None:
    if valor is None or str(valor).strip() == "":
        return None
    return str(valor)


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


def construir_payload(datos: dict[str, Any], lineas: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "fecha": _texto(datos.get("fecha")),
        "cliente_nombre": _texto(datos.get("cliente_nombre")) or "",
        "cliente_ruc": _texto(datos.get("cliente_ruc")),
        "mostrar_ruc": bool(datos.get("mostrar_ruc", True)),
        "cliente_direccion": _texto(datos.get("cliente_direccion")),
        "cliente_telefono": _texto(datos.get("cliente_telefono")),
        "cliente_correo": _texto(datos.get("cliente_correo")),
        "sucursal": _texto(datos.get("sucursal")),
        "vendedor": _texto(datos.get("vendedor")),
        "orden_compra": _texto(datos.get("orden_compra")),
        "condicion_pago": datos.get("condicion_pago") or "contado",
        "portes": _decimal(datos.get("portes")) or "0",
        "notas": _texto(datos.get("notas")),
        "lineas": [
            {
                "orden": indice,
                "descripcion": _texto(linea.get("descripcion")) or "",
                "codigo_barras": _texto(linea.get("codigo_barras")),
                "categoria": _texto(linea.get("categoria")),
                "cantidad": _decimal(linea.get("cantidad")) or "1",
                "precio_unitario": _decimal(linea.get("precio_unitario")) or "0",
                "precio_unidad": _decimal(linea.get("precio_unidad")),
                "descuento_pct": _decimal(linea.get("descuento_pct")) or "0",
                "gravada": bool(linea.get("gravada", True)),
                "unidades_por_caja": int(linea.get("unidades_por_caja") or 1),
                "cobrar_por": linea.get("cobrar_por") or "unidad",
                "producto_id": linea.get("producto_id"),
            }
            for indice, linea in enumerate(lineas, start=1)
        ],
    }


def crear(cliente_api: ClienteApi, payload: dict[str, Any]) -> dict[str, Any]:
    return cliente_api.post("/api/v1/facturas", json=payload)


def obtener_pdf(cliente_api: ClienteApi, factura_id: int) -> bytes:
    return cliente_api.get(f"/api/v1/facturas/{factura_id}/pdf")


@ui.page("/facturacion/nueva")
def pagina_nueva() -> None:
    montar_layout("Nueva factura")

    guardado = sesion.datos_cliente
    cliente_nombre = ui.input("Cliente", value=guardado.get("cliente_nombre", "")).classes("w-full")
    cliente_ruc = ui.input("RUC", value=guardado.get("cliente_ruc", ""))
    mostrar_ruc = ui.checkbox("Mostrar RUC", value=True)
    fecha = ui.date(mask="YYYY-MM-DD")
    condicion = ui.select(CONDICIONES, label="Condición de pago", value="contado")
    portes = ui.number("Portes", value=0, min=0, precision=2)
    orden_compra = ui.input("Orden de compra")
    vendedor = ui.input("Vendedor")

    with ui.row().classes("w-full gap-2"):
        cliente_direccion = ui.input("Dirección").classes("w-full")
        cliente_telefono = ui.input("Teléfono")
        cliente_correo = ui.input("Correo")
        sucursal = ui.input("Sucursal")
    notas = ui.input("Notas").classes("w-full")

    mensajes = ui.column()
    lineas: list[dict[str, Any]] = []
    contenedor_lineas = ui.column().classes("w-full")

    def quitar_linea(tarjeta: Any, modelo: dict[str, Any]) -> None:
        if modelo in lineas:
            lineas.remove(modelo)
        tarjeta.delete()

    def agregar_linea() -> None:
        modelo: dict[str, Any] = {}
        with contenedor_lineas:
            with ui.card().classes("w-full") as tarjeta:
                modelo["descripcion"] = ui.input("Descripción").classes("w-full")
                with ui.row().classes("w-full gap-2"):
                    modelo["cantidad"] = ui.number("Cantidad", value=1, min=0.01, precision=2)
                    modelo["precio_unitario"] = ui.number(
                        "Precio unitario", value=0, min=0, precision=2
                    )
                    modelo["descuento_pct"] = ui.number(
                        "Descuento %", value=0, min=0, max=100, precision=2
                    )
                    modelo["unidades_por_caja"] = ui.number(
                        "Unidades por caja", value=1, min=1, precision=0
                    )
                with ui.row().classes("w-full gap-2 items-center"):
                    modelo["cobrar_por"] = ui.select(
                        COBRAR_POR, label="Cobrar por", value="unidad"
                    )
                    modelo["gravada"] = ui.checkbox("Gravada", value=True)
                    ui.button(
                        "Quitar",
                        on_click=lambda t=tarjeta: quitar_linea(t, modelo),
                    ).classes("ml-auto")
        lineas.append(modelo)

    def leer_lineas() -> list[dict[str, Any]]:
        return [
            {
                "descripcion": modelo["descripcion"].value,
                "cantidad": modelo["cantidad"].value,
                "precio_unitario": modelo["precio_unitario"].value,
                "descuento_pct": modelo["descuento_pct"].value,
                "unidades_por_caja": modelo["unidades_por_caja"].value,
                "cobrar_por": modelo["cobrar_por"].value,
                "gravada": modelo["gravada"].value,
            }
            for modelo in lineas
        ]

    with ui.row().classes("gap-2 my-2"):
        boton_orquidea("Agregar línea", agregar_linea, variante="secundario")
        boton_orquidea("Emitir factura", lambda: guardar())

    resultado = ui.column().classes("w-full")

    def descargar(factura: dict[str, Any]) -> None:
        try:
            contenido = obtener_pdf(cliente, int(factura["id"]))
        except ErrorApi as error:
            notificar(f"No se pudo descargar el PDF: {error.detail}.", "negative")
            return
        ui.download(
            contenido,
            f"factura-{factura['numero_serie']}.pdf",
            media_type="application/pdf",
        )

    def guardar() -> None:
        mensajes.clear()
        resultado.clear()

        datos = {
            "cliente_nombre": cliente_nombre.value,
            "cliente_ruc": cliente_ruc.value,
            "mostrar_ruc": mostrar_ruc.value,
            "fecha": fecha.value,
            "condicion_pago": condicion.value,
            "portes": portes.value,
            "orden_compra": orden_compra.value,
            "vendedor": vendedor.value,
            "cliente_direccion": cliente_direccion.value,
            "cliente_telefono": cliente_telefono.value,
            "cliente_correo": cliente_correo.value,
            "sucursal": sucursal.value,
            "notas": notas.value,
        }
        payload = construir_payload(datos, leer_lineas())

        if not payload["cliente_nombre"] or not payload["lineas"]:
            with mensajes:
                mensaje_error("Ingresá el cliente y al menos una línea.")
            return
        if any(not linea["descripcion"] for linea in payload["lineas"]):
            with mensajes:
                mensaje_error("Todas las líneas necesitan descripción.")
            return

        try:
            factura = crear(cliente, payload)
        except ErrorApi as error:
            with mensajes:
                mensaje_error(f"{error.code}: {error.detail}")
                for item in error.errors:
                    ubicacion = ".".join(str(parte) for parte in item.get("loc", []))
                    texto = item.get("msg") or item.get("detail") or "Valor inválido."
                    mensaje_error(f"{ubicacion}: {texto}")
            return

        sesion.ultima_factura = factura
        with resultado:
            with ui.element("section").classes("orq-ticket w-full") as ticket:
                with ui.row().classes("orq-ticket-cabecera w-full"):
                    with ui.column().classes("gap-0"):
                        ui.label(factura["numero_serie"]).classes("orq-ticket-folio")
                        ui.label("Factura emitida.").classes("orq-ticket-fecha")
                    sello_estado(factura.get("estado", "emitida"))
                campos = (
                    ("Cliente", "cliente_nombre"),
                    ("Fecha", "fecha"),
                    ("Subtotal", "subtotal"),
                    ("Descuento", "descuento_total"),
                    ("ITBMS", "itbms"),
                )
                with ui.column().classes("orq-ticket-datos w-full"):
                    for etiqueta, campo in campos:
                        with ui.element("div").classes("orq-dato"):
                            ui.label(etiqueta).classes("orq-dato-etiqueta")
                            ui.label(_valor(factura, campo)).classes("orq-dato-valor")
                with ui.column().classes("orq-ticket-totales"):
                    total_animado(_valor(factura, "total"))
                boton_orquidea(
                    "Descargar PDF",
                    lambda: descargar(factura),
                    variante="secundario",
                ).classes("mt-4")
        sello_emitir(factura["numero_serie"])
        notificar(f"Factura emitida: {factura['numero_serie']}.")

    agregar_linea()
