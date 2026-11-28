import asyncio
from typing import Any

import httpx
from nicegui import app, ui

from components.forms import (
    boton_enlace,
    boton_orquidea,
    campo_orquidea,
    confirmar_accion,
    mensaje_error,
    mostrar_error,
    notificar,
    numero_orquidea,
    selector_orquidea,
)
from components.layout import montar_layout
from components.shared import estado_cargando, estado_vacio, ticket_resumen
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import actualizar_contador, conectar_storage, sesion

cliente = ClienteApi()

ENVASES = {
    "caja": "Caja",
    "media_caja": "Media caja",
    "unidad": "Unidad",
}

MENSAJE_CONEXION = (
    "No pudimos conectar con el sistema. Revisa tu conexión e inténtalo de nuevo."
)
MENSAJE_REVISION = (
    "Revisa el producto indicado y vuelve a intentarlo. Tu carrito se conserva."
)


def lineas_para_calculo(carrito: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "producto_id": item["producto_id"],
            "tipo_empaque": item["tipo_empaque"],
            "cantidad": str(item["cantidad"]),
        }
        for item in carrito
    ]


def calcular(cliente_api: ClienteApi, carrito: list[dict[str, Any]]) -> dict[str, Any]:
    return cliente_api.post(
        "/api/v1/carrito/calcular",
        json={"lineas": lineas_para_calculo(carrito)},
    )


def leer_carrito(
    carrito: list[dict[str, Any]],
    controles: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Lee la edición de cada línea sin mezclar widgets con los datos guardados."""
    leido = []
    for indice, item in enumerate(carrito):
        control = (controles or {}).get(indice) or {}
        envase = control.get("envase") or item.get("_envase")
        cantidad = control.get("cantidad") or item.get("_cantidad")
        leido.append(
            {
                "producto_id": item["producto_id"],
                "nombre": item["nombre"],
                "tipo_empaque": (
                    str(envase.value or "caja") if envase else item["tipo_empaque"]
                ),
                "cantidad": (
                    float(cantidad.value or 0) if cantidad else float(item["cantidad"])
                ),
            }
        )
    return leido


def listar_clientes(cliente_api: ClienteApi) -> list[dict[str, Any]]:
    return cliente_api.get("/api/v1/clientes", params={"solo_activos": True})


def opciones_empaque(item: dict[str, Any]) -> dict[str, str]:
    opciones = {"caja": "Caja"}
    if item.get("permite_media_caja") and item.get("precio_media_caja") not in (None, ""):
        opciones["media_caja"] = "Media caja"
    opciones["unidad"] = "Unidad"
    actual = str(item.get("tipo_empaque") or "")
    if actual and actual not in opciones:
        opciones[actual] = ENVASES.get(actual, actual)
    return opciones


def construir_lineas_pedido(
    carrito: list[dict[str, Any]], calculo: dict[str, Any]
) -> list[dict[str, Any]]:
    por_clave = {
        (str(linea["producto_id"]), linea["tipo_empaque"]): linea
        for linea in calculo.get("lineas") or []
    }
    lineas = []
    for orden, item in enumerate(carrito, start=1):
        clave = (str(item["producto_id"]), item["tipo_empaque"])
        linea = por_clave.get(clave)
        if linea is None:
            raise ValueError(f"No hay precio actualizado para {item['nombre']}.")
        lineas.append(
            {
                "producto_id": int(item["producto_id"]),
                "tipo_empaque": item["tipo_empaque"],
                "cantidad": str(item["cantidad"]),
                "subtotal": str(linea["subtotal"]),
                "orden": orden,
            }
        )
    return lineas


def construir_pedido(
    cliente_id: int,
    notas: str | None,
    carrito: list[dict[str, Any]],
    calculo: dict[str, Any],
) -> dict[str, Any]:
    lineas = construir_lineas_pedido(carrito, calculo)
    if not lineas:
        raise ValueError("El carrito está vacío.")
    return {
        "cliente_id": int(cliente_id),
        "estado": "pendiente",
        "total_estimado": str(calculo.get("total") or "0"),
        "notas": (notas or "").strip() or None,
        "lineas": lineas,
    }


def crear_pedido(cliente_api: ClienteApi, payload: dict[str, Any]) -> dict[str, Any]:
    return cliente_api.post("/api/v1/pedidos", json=payload)


def es_error_de_conexion(error: Exception) -> bool:
    return isinstance(
        error,
        (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError),
    )


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/carrito")
async def pagina_carrito() -> None:
    await conectar_storage()
    montar_layout("Tu carrito", ruta_activa="/carrito", migas="Productos")

    carrito = sesion.carrito
    mensajes = ui.column().classes("w-full gap-1")
    with ui.element("div").classes("orq-dos-columnas w-full"):
        with ui.element("section").classes("w-full") as lista:
            pass
        with ui.element("section").classes("w-full") as resultado:
            pass

    calculo_actual: dict[str, Any] = {}
    clientes_cargados: dict[str, Any] = {"hecho": False}
    mensajes_pedido: Any = None
    calculo_pendiente: dict[str, Any] = {"valor": False}
    # Los widgets no se guardan: el almacenamiento de la pestaña solo acepta datos.
    controles: dict[int, dict[str, Any]] = {}

    def recalcular() -> None:
        asyncio.create_task(calcular_totales())

    def reintentar_pedido() -> None:
        asyncio.create_task(confirmar_pedido())

    def aviso_con_reintento(contenedor: Any, texto: str, accion: Any) -> None:
        with contenedor:
            mensaje_error(texto)
            boton_orquidea("Reintentar", accion, variante="secundario")

    def reintentar_calculo() -> None:
        recalcular()

    def cambiar_cantidad(indice: int, valor: Any) -> None:
        if calculo_pendiente["valor"] or indice >= len(carrito):
            return
        try:
            cantidad = float(valor)
        except (TypeError, ValueError):
            return
        if cantidad <= 0:
            notificar("Elige una cantidad mayor a cero.", tipo="warning")
            return
        carrito[indice]["cantidad"] = cantidad
        recalcular()

    def cambiar_empaque(indice: int, valor: Any) -> None:
        if calculo_pendiente["valor"] or indice >= len(carrito):
            return
        item = carrito[indice]
        empaque = str(valor)
        if empaque not in opciones_empaque(item):
            notificar("Esta presentación no está disponible para el producto.", tipo="warning")
            envase = (controles.get(indice) or {}).get("envase")
            if envase is not None:
                envase.value = item["tipo_empaque"]
                envase.update()
            return
        item["tipo_empaque"] = empaque
        recalcular()

    def quitar(item: dict[str, Any]) -> None:
        if item in carrito:
            carrito.remove(item)
        actualizar_contador(carrito)
        mensajes.clear()
        resultado.clear()
        calculo_actual.clear()
        notificar("Producto quitado del carrito.")
        pintar()
        if carrito:
            recalcular()

    def pintar() -> None:
        lista.clear()
        controles.clear()
        if not carrito:
            with lista:
                estado_vacio(
                    "Tu carrito está vacío. Añade productos desde el catálogo",
                    "Elige productos, presentación y cantidad para empezar.",
                )
                boton_enlace("Ver catálogo", "/catalogo")
            return

        with lista:
            with ui.element("div").classes(
                "orq-linea orq-linea-carrito orq-linea-cabecera w-full"
            ):
                ui.label("Producto")
                ui.label("Presentación")
                ui.label("Cantidad")
                ui.label("Precio")
                ui.label("Subtotal")
                ui.label("")

        for indice, item in enumerate(carrito):
            with lista:
                with ui.element("div").classes(
                    "orq-linea orq-linea-carrito w-full items-center"
                ):
                    ui.label(_valor(item, "nombre")).classes("orq-entrada-titulo")
                    envase = selector_orquidea(
                        "Presentación",
                        opciones_empaque(item),
                        value=item["tipo_empaque"],
                        buscar=False,
                    )
                    cantidad = numero_orquidea(
                        "Cantidad",
                        value=float(item["cantidad"]),
                        min=0.01,
                        precision=2,
                    )
                    precio = ui.label("—").classes(
                        "orq-resumen tabular-nums text-right"
                    )
                    subtotal = ui.label("—").classes(
                        "orq-resumen tabular-nums text-right"
                    )
                    boton_orquidea(
                        "Quitar",
                        lambda i=item: quitar(i),
                        variante="secundario",
                    )
                    controles[indice] = {
                        "envase": envase,
                        "cantidad": cantidad,
                        "precio": precio,
                        "subtotal": subtotal,
                    }
                    envase.on_value_change(
                        lambda evento, i=indice: cambiar_empaque(i, evento.value)
                    )
                    cantidad.on_value_change(
                        lambda evento, i=indice: cambiar_cantidad(i, evento.value)
                    )

    async def calcular_totales() -> None:
        mensajes.clear()
        resultado.clear()
        calculo_actual.clear()
        if not carrito:
            return
        with resultado:
            estado_cargando(3)
        calculo_pendiente["valor"] = True
        await asyncio.sleep(0.12)
        leido = leer_carrito(carrito, controles)
        if any(float(linea["cantidad"]) <= 0 for linea in leido):
            calculo_pendiente["valor"] = False
            resultado.clear()
            notificar("Elige una cantidad mayor a cero.", tipo="warning")
            return
        for item, valores in zip(carrito, leido):
            item["tipo_empaque"] = valores["tipo_empaque"]
            item["cantidad"] = valores["cantidad"]
        try:
            datos = await asyncio.to_thread(calcular, cliente, carrito)
        except ErrorApi as error:
            calculo_pendiente["valor"] = False
            resultado.clear()
            mostrar_error(mensajes, error)
            with mensajes:
                mensaje_error(MENSAJE_REVISION)
            return
        except Exception as error:
            calculo_pendiente["valor"] = False
            resultado.clear()
            texto = MENSAJE_CONEXION if es_error_de_conexion(error) else (
                "No pudimos calcular el carrito. Inténtalo de nuevo."
            )
            aviso_con_reintento(mensajes, texto, reintentar_calculo)
            return
        calculo_actual.update(datos)
        lineas = [
            {
                "descripcion": (
                    f"{_valor(linea, 'descripcion')} · "
                    f"{ENVASES.get(str(linea.get('tipo_empaque')), 'Presentación')} × "
                    f"{_valor(linea, 'cantidad')}"
                ),
                "importe": _valor(linea, "subtotal"),
            }
            for linea in datos.get("lineas") or []
        ]
        resultado.clear()
        with resultado:
            ticket_resumen(datos, lineas, titulo="Totales del carrito")
        for indice, linea in enumerate(datos.get("lineas") or []):
            control = controles.get(indice) or {}
            precio = control.get("precio")
            subtotal = control.get("subtotal")
            if precio is not None:
                precio.text = _valor(linea, "precio_unitario")
            if subtotal is not None:
                subtotal.text = _valor(linea, "subtotal")
        calculo_pendiente["valor"] = False

    def vaciar() -> None:
        carrito.clear()
        mensajes.clear()
        mensajes_pedido.clear()
        resultado.clear()
        calculo_actual.clear()
        actualizar_contador(carrito)
        notificar("Carrito vacío")
        pintar()

    def pedir_vaciado() -> None:
        if not carrito:
            return
        confirmar_accion(
            "Vaciar el carrito",
            "Se quitarán todos los productos. ¿Continuar?",
            vaciar,
            etiqueta_confirmar="Vaciar",
        )

    def cargar_clientes() -> None:
        if clientes_cargados["hecho"]:
            return
        try:
            datos = listar_clientes(cliente)
        except ErrorApi as error:
            mostrar_error(mensajes_pedido, error)
            return
        except Exception:
            aviso_con_reintento(
                mensajes_pedido, MENSAJE_CONEXION, cargar_clientes
            )
            return
        opciones: dict[Any, str] = {0: "Selecciona un cliente"}
        for item in datos:
            opciones[int(item["id"])] = _valor(item, "nombre_empresa")
        selector_cliente.options = opciones
        selector_cliente.update()
        clientes_cargados["hecho"] = True

    def abrir_confirmacion() -> None:
        mensajes_pedido.clear()
        cargar_clientes()
        dialogo.open()

    async def confirmar_pedido() -> None:
        mensajes_pedido.clear()
        if not selector_cliente.value:
            with mensajes_pedido:
                mensaje_error("Elige un cliente para continuar.")
            return
        if not calculo_actual:
            await calcular_totales()
        if not calculo_actual:
            with mensajes_pedido:
                mensaje_error(MENSAJE_REVISION)
            return
        try:
            payload = construir_pedido(
                int(selector_cliente.value), notas.value, carrito, calculo_actual
            )
        except ValueError as error:
            with mensajes_pedido:
                mensaje_error(str(error))
            return
        try:
            pedido = await asyncio.to_thread(crear_pedido, cliente, payload)
        except ErrorApi as error:
            mostrar_error(mensajes_pedido, error)
            if error.status_code in (404, 409, 422):
                with mensajes_pedido:
                    mensaje_error(MENSAJE_REVISION)
            return
        except Exception:
            aviso_con_reintento(
                mensajes_pedido, MENSAJE_CONEXION, reintentar_pedido
            )
            return
        carrito.clear()
        app.storage.tab["aviso"] = "Pedido creado"
        actualizar_contador(carrito)
        dialogo.close()
        notificar("Pedido creado")
        ui.navigate.to(f"/pedidos/detalle?pedido_id={pedido['id']}")

    with ui.dialog() as dialogo, ui.card().classes("orq-confirmacion"):
        ui.label("Confirmar pedido").classes("orq-confirmacion-titulo")
        with ui.column().classes("w-full gap-2"):
            selector_cliente = selector_orquidea(
                "Buscar cliente", {0: "Selecciona un cliente"}, value=0
            ).classes("w-full")
            notas = campo_orquidea(
                "Notas", placeholder="Entrega, horario o referencias"
            ).classes("w-full")
        with ui.row().classes("orq-confirmacion-acciones w-full"):
            boton_orquidea("Cancelar", dialogo.close, variante="secundario")
            boton_orquidea("Confirmar pedido", confirmar_pedido)
        mensajes_pedido = ui.column().classes("w-full gap-1")

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Confirmar pedido", abrir_confirmacion)
        boton_orquidea("Vaciar", pedir_vaciado, variante="peligro")
        boton_enlace("Seguir comprando", "/catalogo", variante="secundario")

    pintar()
    if carrito:
        await calcular_totales()
