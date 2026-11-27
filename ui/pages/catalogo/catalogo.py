from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

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


def agregar_al_carrito(
    carrito: list[dict[str, Any]],
    producto: dict[str, Any],
    tipo_empaque: str,
    cantidad: float,
) -> None:
    for item in carrito:
        if (
            item["producto_id"] == producto["id"]
            and item["tipo_empaque"] == tipo_empaque
        ):
            item["cantidad"] = float(item["cantidad"]) + float(cantidad)
            return
    carrito.append(
        {
            "producto_id": producto["id"],
            "nombre": producto["nombre"],
            "tipo_empaque": tipo_empaque,
            "cantidad": float(cantidad),
        }
    )


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/catalogo")
def pagina_catalogo() -> None:
    montar_layout("Catálogo")

    mensajes = ui.column()
    busqueda = ui.input("Buscar producto").classes("w-full")
    categoria = ui.select({"": "Todas"}, label="Categoría", value="")
    productos = ui.column().classes("w-full")

    def cargar_categorias() -> None:
        try:
            datos = listar_categorias(cliente)
        except ErrorApi as error:
            mensajes.clear()
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            return
        opciones: dict[Any, str] = {"": "Todas"}
        for item in datos:
            opciones[item["id"]] = item["nombre"]
        categoria.options = opciones
        categoria.update()

    def cargar_productos() -> None:
        mensajes.clear()
        productos.clear()
        texto = (busqueda.value or "").strip()
        seleccionada = categoria.value
        id_categoria = int(seleccionada) if seleccionada not in (None, "") else None
        try:
            datos = listar_productos(cliente, texto or None, id_categoria)
        except ErrorApi as error:
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            return

        if not datos:
            with productos:
                ui.label("No hay productos para esos filtros.").classes("text-grey")
            return

        for producto in datos:
            with productos:
                with ui.card().classes("w-full"):
                    ui.label(producto["nombre"]).classes("text-h6")
                    ui.label(f"SKU: {_valor(producto, 'sku')}").classes("text-caption")
                    with ui.row().classes("w-full gap-2"):
                        ui.label(f"Caja: {_valor(producto, 'precio_caja')}")
                        ui.label(f"Unidad: {_valor(producto, 'precio_unidad')}")
                    with ui.row().classes("w-full gap-2 items-center"):
                        envase = ui.select(ENVASES, label="Presentación", value="caja")
                        cantidad = ui.number("Cantidad", value=1, min=0.01, precision=2)
                        ui.button(
                            "Agregar",
                            on_click=lambda p=producto, e=envase, c=cantidad: agregar(
                                p, e, c
                            ),
                        )

    def agregar(producto: dict[str, Any], envase: Any, cantidad: Any) -> None:
        total = float(cantidad.value or 0)
        if total <= 0:
            ui.notify("La cantidad debe ser mayor a cero.", type="negative")
            return
        agregar_al_carrito(
            sesion.carrito,
            producto,
            str(envase.value or "caja"),
            total,
        )
        ui.notify("Producto agregado al carrito.", type="positive")

    with ui.row().classes("gap-2 my-2"):
        ui.button("Buscar", on_click=cargar_productos)
        ui.button("Ver carrito", on_click=lambda: ui.navigate.to("/carrito"))

    cargar_categorias()
    cargar_productos()
