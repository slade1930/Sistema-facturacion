"""Catálogo filtrado por sector para la empresa; etapa B."""

import asyncio
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
from components.portal import montar_portal
from components.shared import (
    en_oferta,
    estado_cargando,
    estado_vacio,
    precio_con_descuento,
)
from pages.catalogo.catalogo import agregar_al_carrito, opciones_empaque
from state import auth
from state.cliente_api import ErrorApi
from state.sesion import actualizar_contador, sesion


def listar_categorias(api: Any) -> list[dict[str, Any]]:
    return api.get("/api/v1/categorias")


def listar_productos(
    api: Any, busqueda: str | None = None, categoria_id: int | None = None
) -> list[dict[str, Any]]:
    parametros: dict[str, Any] = {}
    if busqueda:
        parametros["busqueda"] = busqueda
    if categoria_id is not None:
        parametros["categoria_id"] = categoria_id
    return api.get("/api/v1/productos", params=parametros)


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/portal/catalogo")
async def pagina_catalogo_empresa() -> None:
    await auth.conectar()
    if not auth.exigir_sesion():
        return
    montar_portal("Catálogo de mi sector", ruta_activa="/portal/catalogo")

    mensajes = ui.column().classes("w-full")
    productos = ui.column().classes("w-full gap-3")
    with ui.element("div").classes("orq-filtros w-full"):
        busqueda = campo_orquidea("Buscar producto", placeholder="Nombre o SKU")
        categoria = selector_orquidea("Categoría", {"": "Todas"}, value="")

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
            notificar("Presentación no disponible para este producto.", tipo="warning")
            return
        agregar_al_carrito(sesion.carrito, producto, empaque, total)
        actualizar_contador(sesion.carrito)
        notificar("Producto añadido al carrito.")

    def pintar(datos: list[dict[str, Any]]) -> None:
        productos.clear()
        if not datos:
            with productos:
                estado_vacio(
                    "No hay productos con esos filtros.",
                    "Prueba con otro nombre o categoría.",
                )
            return
        for indice, producto in enumerate(datos):
            with productos:
                disponible = bool(producto.get("estado_activo", True))
                acentos = (
                    "border-top: 3px solid var(--orq-fucsia)",
                    "border-left: 3px solid var(--orq-fucsia)",
                )
                with ui.element("article").classes("orq-entrada w-full").style(
                    f"{acentos[indice % len(acentos)]}; "
                    "box-shadow: none !important"
                ):
                    ui.label(str(producto["nombre"])).classes("orq-entrada-titulo")
                    ui.label(f"SKU: {_valor(producto, 'sku')}").classes("orq-ayuda")
                    if _valor(producto, "marca"):
                        ui.label(f"Marca: {_valor(producto, 'marca')}").classes(
                            "orq-ayuda"
                        )
                    if _valor(producto, "presentacion"):
                        ui.label(
                            f"Presentación: {_valor(producto, 'presentacion')}"
                        ).classes("orq-ayuda")
                    if not disponible:
                        ui.label("No disponible").classes("orq-ayuda")
                    descuento = _valor(producto, "descuento_pct") or "0"
                    if en_oferta(producto):
                        ui.label(f"Oferta {descuento} %").classes(
                            "orq-sello orq-sello--neutro"
                        )
                    with ui.column().classes("gap-0 mt-2"):
                        ui.label(
                            f"Unidad: {precio_con_descuento(producto.get('precio_unidad'), descuento)}"
                            + (
                                f" (antes {_valor(producto, 'precio_unidad')})"
                                if en_oferta(producto)
                                else ""
                            )
                        ).classes("orq-resumen tabular-nums")
                        ui.label(
                            f"Caja: {precio_con_descuento(producto.get('precio_caja'), descuento)}"
                            + (
                                f" (antes {_valor(producto, 'precio_caja')})"
                                if en_oferta(producto)
                                else ""
                            )
                        ).classes("orq-resumen tabular-nums")
                        if producto.get("permite_media_caja") and producto.get(
                            "precio_media_caja"
                        ) is not None:
                            ui.label(
                                f"Media caja: {precio_con_descuento(producto.get('precio_media_caja'), descuento)}"
                                + (
                                    f" (antes {_valor(producto, 'precio_media_caja')})"
                                    if en_oferta(producto)
                                    else ""
                                )
                            ).classes("orq-resumen tabular-nums")
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

    async def cargar() -> None:
        api = auth.cliente_portal()
        mensajes.clear()
        productos.clear()
        with productos:
            estado_cargando(3)
        try:
            categorias, datos = await asyncio.gather(
                asyncio.to_thread(listar_categorias, api),
                asyncio.to_thread(listar_productos, api),
            )
        except ErrorApi as error:
            productos.clear()
            mostrar_error(mensajes, error)
            return
        except Exception:
            productos.clear()
            with mensajes:
                ui.label("No pudimos cargar el catálogo. Inténtalo de nuevo.").classes(
                    "orq-error"
                )
            return
        opciones: dict[Any, str] = {"": "Todas"}
        for item in categorias:
            opciones[item["id"]] = str(item.get("nombre") or "")
        categoria.options = opciones
        categoria.update()
        pintar(datos)

    async def filtrar() -> None:
        seleccion = categoria.value
        id_categoria = int(seleccion) if seleccion not in (None, "") else None
        api = auth.cliente_portal()
        mensajes.clear()
        try:
            datos = await asyncio.to_thread(
                listar_productos,
                api,
                (busqueda.value or "").strip() or None,
                id_categoria,
            )
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        pintar(datos)

    busqueda.on("keydown.enter", lambda *args: asyncio.create_task(filtrar()))
    categoria.on_value_change(lambda *args: asyncio.create_task(filtrar()))
    with ui.row().classes("orq-barra-acciones w-full"):
        boton_orquidea("Buscar", lambda: asyncio.create_task(filtrar()))
        boton_enlace("Ver carrito", "/portal/carrito", variante="secundario")

    asyncio.create_task(cargar())


__all__ = ["listar_categorias", "listar_productos", "pagina_catalogo_empresa"]
