from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from nicegui import ui

from components.forms import (
    barra_acciones,
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    notificar,
    numero_orquidea,
    selector_orquidea,
    seccion_formulario,
)
from components.layout import montar_layout
from components.shared import sello_emitir, sello_estado, ticket_resumen
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


def descargar_pdf(cliente_api: ClienteApi, factura_id: int) -> bytes:
    return obtener_pdf(cliente_api, factura_id)


def listar_clientes(
    cliente_api: ClienteApi, busqueda: str | None = None
) -> list[dict[str, Any]]:
    parametros: dict[str, Any] = {"solo_activos": True}
    if busqueda:
        parametros["busqueda"] = busqueda
    datos = cliente_api.get("/api/v1/clientes", params=parametros)
    return datos if isinstance(datos, list) else []


def _decimal_seguro(valor: Any, defecto: str = "0") -> Decimal:
    if valor is None or str(valor).strip() == "":
        return Decimal(defecto)
    try:
        return Decimal(str(valor))
    except Exception:
        return Decimal(defecto)


def _centavos(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _dinero(valor: Decimal) -> str:
    return f"{_centavos(valor):.2f}"


def calcular_resumen(
    lineas: list[dict[str, Any]], portes: Any = 0
) -> dict[str, Any]:
    """Vista previa de totales, con las mismas reglas que la factura emitida."""
    bruto_total = Decimal("0")
    base_gravada = Decimal("0")
    base_exenta = Decimal("0")
    hay_descuento = False
    resumen_lineas: list[dict[str, str]] = []

    for linea in lineas:
        cantidad = _decimal_seguro(linea.get("cantidad"), "1")
        precio = _decimal_seguro(linea.get("precio_unitario"), "0")
        if str(linea.get("cobrar_por") or "unidad") != "caja":
            precio_unidad = _decimal_seguro(linea.get("precio_unidad"), "0")
            if precio_unidad > 0:
                precio = precio_unidad

        descuento = min(
            max(_decimal_seguro(linea.get("descuento_pct"), "0"), Decimal("0")),
            Decimal("100"),
        )
        hay_descuento = hay_descuento or descuento > 0

        bruto = cantidad * precio
        if descuento >= 100:
            monto = Decimal("0")
        elif descuento > 0:
            monto = _centavos(bruto * (Decimal("100") - descuento) / Decimal("100"))
        else:
            monto = _centavos(bruto)

        if bool(linea.get("gravada", True)):
            base_gravada += monto
        else:
            base_exenta += monto
        bruto_total += bruto
        resumen_lineas.append(
            {
                "descripcion": _texto(linea.get("descripcion")) or "Línea",
                "importe": _dinero(monto),
            }
        )

    base = base_gravada + base_exenta
    if hay_descuento:
        subtotal = _centavos(bruto_total)
        descuento_total = max(Decimal("0"), _centavos(subtotal - base))
    else:
        subtotal = _centavos(base)
        descuento_total = Decimal("0")

    itbms = _centavos(base_gravada * Decimal("0.07"))
    total = _centavos(base + itbms + _decimal_seguro(portes, "0"))

    return {
        "subtotal": _dinero(subtotal),
        "descuento_total": _dinero(descuento_total),
        "itbms": _dinero(itbms),
        "total": _dinero(total),
        "lineas": resumen_lineas,
    }


@ui.page("/facturacion/nueva")
def pagina_nueva() -> None:
    montar_layout("Nueva factura", ruta_activa="/facturacion/nueva")

    guardado = sesion.datos_cliente
    catalogo: dict[str, dict[str, Any]] = {}
    try:
        for item in listar_clientes(cliente):
            nombre = _texto(item.get("nombre_empresa"))
            if nombre:
                catalogo[nombre] = item
    except Exception:
        catalogo = {}

    nombre_guardado = _texto(guardado.get("cliente_nombre"))
    opciones_clientes = list(catalogo)
    if nombre_guardado and nombre_guardado not in opciones_clientes:
        opciones_clientes.insert(0, nombre_guardado)

    lineas: list[dict[str, Any]] = []
    ultimo_cliente: dict[str, str | None] = {"nombre": None}
    firma_resumen: dict[str, Any] = {"valor": None}
    emitida: dict[str, bool] = {"valor": False}

    def quitar_linea(tarjeta: Any, modelo: dict[str, Any]) -> None:
        if modelo in lineas:
            lineas.remove(modelo)
        tarjeta.delete()
        actualizar_resumen()

    def agregar_linea() -> None:
        modelo: dict[str, Any] = {}
        with contenedor_lineas:
            with ui.element("div").classes("orq-linea w-full") as tarjeta:
                modelo["descripcion"] = campo_orquidea("Descripción")
                modelo["cantidad"] = numero_orquidea(
                    "Cantidad", value=1, min=0.01, precision=2
                )
                modelo["precio_unitario"] = numero_orquidea(
                    "Precio", moneda=True, value=0, min=0, precision=2
                )
                modelo["descuento_pct"] = numero_orquidea(
                    "Descuento %", value=0, min=0, max=100, precision=2
                )
                modelo["cobrar_por"] = selector_orquidea(
                    "Cobrar por", COBRAR_POR, buscar=False, value="unidad"
                )
                boton_orquidea(
                    "Quitar",
                    lambda t=tarjeta: quitar_linea(t, modelo),
                    variante="secundario",
                )
                with ui.row().classes("col-span-full items-center gap-4"):
                    modelo["unidades_por_caja"] = numero_orquidea(
                        "Unidades por caja", value=1, min=1, precision=0
                    )
                    modelo["gravada"] = ui.checkbox("Gravada", value=True)
        lineas.append(modelo)
        actualizar_resumen()

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

    def sincronizar_cliente() -> None:
        elegido = _texto(cliente_selector.value)
        if ultimo_cliente["nombre"] == elegido:
            return
        ultimo_cliente["nombre"] = elegido
        if not elegido or elegido not in catalogo:
            return
        item = catalogo[elegido]
        nombre_cliente.value = elegido
        cliente_ruc.value = _valor(item, "ruc")
        cliente_direccion.value = _valor(item, "direccion")
        cliente_telefono.value = _valor(item, "telefono")
        cliente_correo.value = _valor(item, "email_contacto")

    def leer_datos() -> dict[str, Any]:
        elegido = _texto(cliente_selector.value)
        item = catalogo.get(elegido, {}) if elegido else {}

        def dato(control: Any, clave: str) -> Any:
            return _texto(control.value) or item.get(clave)

        return {
            "cliente_nombre": elegido or _texto(nombre_cliente.value),
            "cliente_ruc": dato(cliente_ruc, "ruc"),
            "mostrar_ruc": mostrar_ruc.value,
            "fecha": fecha.value,
            "condicion_pago": condicion.value,
            "portes": portes.value,
            "orden_compra": orden_compra.value,
            "vendedor": vendedor.value,
            "cliente_direccion": dato(cliente_direccion, "direccion"),
            "cliente_telefono": dato(cliente_telefono, "telefono"),
            "cliente_correo": dato(cliente_correo, "email_contacto"),
            "sucursal": sucursal.value,
            "notas": notas.value,
        }

    def actualizar_resumen() -> None:
        if emitida["valor"]:
            return
        calculo = calcular_resumen(leer_lineas(), portes.value)
        firma = (
            calculo["subtotal"],
            calculo["descuento_total"],
            calculo["itbms"],
            calculo["total"],
            tuple(
                (linea["descripcion"], linea["importe"])
                for linea in calculo["lineas"]
            ),
        )
        if firma == firma_resumen["valor"]:
            return
        firma_resumen["valor"] = firma
        resumen.clear()
        with resumen:
            ticket_resumen(calculo, lineas=calculo["lineas"])

    def descargar(factura: dict[str, Any]) -> None:
        try:
            contenido = descargar_pdf(cliente, int(_valor(factura, "id")))
        except (ErrorApi, ValueError, TypeError):
            notificar("No se pudo descargar el PDF.", "negative")
            return
        ui.download(
            contenido,
            f"factura-{_valor(factura, 'numero_serie')}.pdf",
            media_type="application/pdf",
        )

    def pintar_emision(factura: dict[str, Any]) -> None:
        resumen.clear()
        with resumen:
            ui.label("Factura emitida").classes("orq-seccion-titulo")
            with ui.row().classes("orq-ticket-cabecera w-full"):
                with ui.column().classes("gap-0"):
                    ui.label(_valor(factura, "numero_serie")).classes(
                        "orq-ticket-folio"
                    )
                    ui.label(f"Fecha {_valor(factura, 'fecha')}").classes(
                        "orq-ticket-fecha"
                    )
                sello_estado(_valor(factura, "estado") or "emitida")
            ticket_resumen(
                {
                    "subtotal": _valor(factura, "subtotal") or "0.00",
                    "descuento_total": _valor(factura, "descuento_total") or "0.00",
                    "itbms": _valor(factura, "itbms") or "0.00",
                    "total": _valor(factura, "total") or "0.00",
                }
            )
            with ui.row().classes("orq-ticket-acciones w-full"):
                boton_orquidea(
                    "Descargar PDF",
                    lambda: descargar(factura),
                    variante="secundario",
                )
                ui.link(
                    "Ver factura",
                    f"/facturacion/detalle?factura_id={_valor(factura, 'id')}",
                ).classes("orq-boton orq-boton--texto")
                ui.link("Ver historial", "/facturacion/historial").classes(
                    "orq-boton orq-boton--texto"
                )

    def guardar() -> None:
        mensajes.clear()
        sincronizar_cliente()
        datos = leer_datos()
        payload = construir_payload(datos, leer_lineas())

        if not payload["cliente_nombre"] or not payload["lineas"]:
            with mensajes:
                ui.label("Ingresa el cliente y al menos una línea.").classes(
                    "orq-error"
                )
            return
        if any(not linea["descripcion"] for linea in payload["lineas"]):
            with mensajes:
                ui.label("Todas las líneas necesitan descripción.").classes(
                    "orq-error"
                )
            return

        try:
            factura = crear(cliente, payload)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return

        sesion.ultima_factura = factura
        emitida["valor"] = True
        pintar_emision(factura)
        sello_emitir(_valor(factura, "numero_serie"))
        notificar("Factura emitida")

    def al_ticar() -> None:
        if emitida["valor"]:
            return
        sincronizar_cliente()
        actualizar_resumen()

    with ui.element("div").classes("orq-dos-columnas w-full"):
        with ui.column().classes("w-full"):
            with seccion_formulario(
                "Datos del cliente",
                "Elige un cliente guardado o completa sus datos a mano.",
            ):
                cliente_selector = selector_orquidea(
                    "Buscar cliente", opciones_clientes, value=nombre_guardado
                )
                nombre_cliente = campo_orquidea(
                    "Cliente", value=nombre_guardado or ""
                )
                cliente_ruc = campo_orquidea(
                    "RUC", value=_valor(guardado, "cliente_ruc")
                )
                cliente_direccion = campo_orquidea(
                    "Dirección", value=_valor(guardado, "cliente_direccion")
                )
                cliente_telefono = campo_orquidea(
                    "Teléfono", value=_valor(guardado, "cliente_telefono")
                )
                cliente_correo = campo_orquidea(
                    "Correo", value=_valor(guardado, "cliente_correo")
                )
                sucursal = campo_orquidea("Sucursal", value=_valor(guardado, "sucursal"))
                mostrar_ruc = ui.checkbox("Mostrar RUC", value=True)
                ui.label(
                    "Si el cliente no está en la lista, completa sus datos acá."
                ).classes("orq-ayuda")

            with seccion_formulario(
                "Detalles de la factura", "Datos que aparecen en el comprobante."
            ):
                with ui.column().classes("w-full gap-0"):
                    ui.label("Fecha").classes("orq-dato-etiqueta")
                    fecha = ui.date(mask="YYYY-MM-DD").classes("orq-campo w-full")
                condicion = selector_orquidea(
                    "Condición de pago", CONDICIONES, buscar=False, value="contado"
                )
                portes = numero_orquidea(
                    "Portes", moneda=True, value=0, min=0, precision=2
                )
                orden_compra = campo_orquidea("Orden de compra")
                vendedor = campo_orquidea("Vendedor")

            with seccion_formulario(
                "Líneas",
                "Cada producto o servicio va en su propio renglón.",
                rejilla=False,
            ):
                with ui.element("div").classes("orq-linea orq-linea-cabecera w-full"):
                    for texto in (
                        "Descripción",
                        "Cantidad",
                        "Precio",
                        "Descuento %",
                        "Cobrar por",
                        "",
                    ):
                        ui.label(texto)

                contenedor_lineas = ui.column().classes("w-full")

                boton_orquidea(
                    "Agregar línea", agregar_linea, variante="secundario"
                ).classes("mt-2")

            with seccion_formulario("Notas", "Un mensaje opcional para el cliente."):
                notas = campo_orquidea("Notas")

            mensajes = ui.column()

            barra_acciones(
                "Emitir factura", guardar, destino_cancelar="/facturacion/historial"
            )

        with ui.column().classes("w-full orq-resumen"):
            resumen = ui.column().classes("w-full")
            ui.label(
                "El total se actualiza mientras completas las líneas."
            ).classes("orq-ayuda")

    ui.timer(0.5, al_ticar)
    actualizar_resumen()
    agregar_linea()
