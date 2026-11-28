from typing import Any

from nicegui import ui

from components.forms import (
    boton_enlace,
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    notificar,
    numero_orquidea,
    selector_orquidea,
)
from components.layout import montar_layout
from components.shared import estado_vacio
from state.cliente_api import ClienteApi
from state.sesion import actualizar_contador, conectar_storage, sesion

cliente = ClienteApi()

ENVASES = {
    "caja": "Caja",
    "media_caja": "Media caja",
    "unidad": "Unidad",
}


def listar_categorias(cliente_api: ClienteApi) -> list[dict[str, Any]]:
    return cliente_api.get("/api/v1/categorias")


def listar_productos(
    cliente_api: ClienteApi,
    busqueda: str | None = None,
    categoria_id: int | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    if busqueda:
        params["busqueda"] = busqueda
    if categoria_id is not None:
        params["categoria_id"] = categoria_id
    return cliente_api.get("/api/v1/productos", params=params)


def opciones_empaque(producto: dict[str, Any]) -> dict[str, str]:
    """Solo ofrece media caja cuando el producto la permite."""
    opciones = {"caja": "Caja"}
    if producto.get("permite_media_caja") and producto.get("precio_media_caja") not in (None, ""):
        opciones["media_caja"] = "Media caja"
    opciones["unidad"] = "Unidad"
    return opciones


def agregar_al_carrito(
    carrito: list[dict[str, Any]],
    producto: dict[str, Any],
    tipo_empaque: str,
    cantidad: float,
) -> None:
    datos = {
        "producto_id": producto["id"],
        "nombre": producto["nombre"],
        "tipo_empaque": tipo_empaque,
        "cantidad": float(cantidad),
        "precio_caja": producto.get("precio_caja"),
        "precio_media_caja": producto.get("precio_media_caja"),
        "precio_unidad": producto.get("precio_unidad"),
        "permite_media_caja": bool(producto.get("permite_media_caja")),
        "estado_activo": producto.get("estado_activo", True),
    }
    for item in carrito:
        if (
            item["producto_id"] == producto["id"]
            and item["tipo_empaque"] == tipo_empaque
        ):
            item["cantidad"] = float(item["cantidad"]) + float(cantidad)
            item.update({clave: valor for clave, valor in datos.items() if clave != "cantidad"})
            return
    carrito.append(datos)


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/catalogo")
async def pagina_catalogo() -> None:
    await conectar_storage()
    montar_layout("Productos y precios", ruta_activa="/catalogo")

    mensajes = ui.column().classes("w-full")
    productos = ui.column().classes("w-full gap-3")

    with ui.element("div").classes("orq-filtros w-full"):
        with ui.element("div").classes("orq-entradas w-full"):
            busqueda = campo_orquidea(
                "Buscar producto", placeholder="Nombre o SKU"
            )
            categoria = selector_orquidea(
                "Categoría", {"": "Todas"}, value=""
            )

    def cargar_categorias() -> None:
        mensajes.clear()
        try:
            datos = listar_categorias(cliente)
        except Exception as error:
            mostrar_error(mensajes, error)
            return
        opciones: dict[Any, str] = {"": "Todas"}
        for item in datos:
            opciones[item["id"]] = item["nombre"]
        categoria.options = opciones
        categoria.update()

    def agregar(producto: dict[str, Any], envase: Any, cantidad: Any) -> None:
        if not producto.get("estado_activo", True):
            notificar("Este producto no está disponible.", tipo="warning")
            return
        total = float(cantidad.value or 0)
        if total <= 0:
            notificar("Elige una cantidad mayor a cero.", tipo="warning")
            return
        empaque = str(envase.value or "caja")
        if empaque not in opciones_empaque(producto):
            notificar("Elige una presentación disponible para este producto.", tipo="warning")
            return
        agregar_al_carrito(sesion.carrito, producto, empaque, total)
        notificar("Producto añadido")
        actualizar_contador(sesion.carrito)

    def _tarjeta(producto: dict[str, Any], indice: int) -> None:
        disponible = bool(producto.get("estado_activo", True))
        acentos = (
            "border-top: 3px solid var(--orq-fucsia)",
            "border-left: 3px solid var(--orq-fucsia)",
        )
        with ui.element("article").classes("orq-entrada w-full").style(
            f"{acentos[indice % len(acentos)]}; box-shadow: none !important"
        ):
            with ui.row().classes("w-full items-start justify-between gap-4"):
                with ui.column().classes("gap-0"):
                    ui.label(str(producto["nombre"])).classes("orq-entrada-titulo")
                    ui.label(f"SKU: {_valor(producto, 'sku')}").classes("orq-ayuda")
                    if not disponible:
                        ui.label("No disponible").classes("orq-ayuda")
                with ui.column().classes("items-end gap-0"):
                    ui.label("$").classes("orq-entrada-numero")
                    ui.label(f"Caja: {_valor(producto, 'precio_caja')}").classes(
                        "orq-resumen tabular-nums text-right"
                    )
                    ui.label(
                        f"Unidad: {_valor(producto, 'precio_unidad')}"
                    ).classes("orq-resumen tabular-nums text-right")

            with ui.row().classes("w-full items-end gap-3 mt-3"):
                envase = selector_orquidea(
                    "Presentación",
                    opciones_empaque(producto),
                    value="caja",
                    buscar=False,
                )
                cantidad = numero_orquidea(
                    "Cantidad", value=1, min=0.01, precision=2
                )
                boton = boton_orquidea(
                    "Añadir al carrito",
                    lambda p=producto, e=envase, c=cantidad: agregar(p, e, c),
                )
                if not disponible:
                    boton.disable()

    def cargar_productos() -> None:
        mensajes.clear()
        productos.clear()
        texto = (busqueda.value or "").strip()
        seleccionada = categoria.value
        id_categoria = int(seleccionada) if seleccionada not in (None, "") else None
        try:
            datos = listar_productos(cliente, texto or None, id_categoria)
        except Exception as error:
            mostrar_error(mensajes, error)
            return

        if not datos:
            with productos:
                estado_vacio(
                    "No encontramos productos con esos filtros.",
                    "Prueba con otro nombre o categoría.",
                )
            return

        for indice, producto in enumerate(datos):
            with productos:
                _tarjeta(producto, indice)

    busqueda.on("keydown.enter", cargar_productos)
    categoria.on_value_change(cargar_productos)

    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Buscar", cargar_productos)
        boton_enlace("Ver carrito", "/carrito", variante="secundario")

    cargar_categorias()
    cargar_productos()
