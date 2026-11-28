"""Catálogo global: productos y categorías del administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    SECTORES_ADMIN,
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    montar_admin,
    numero,
    tabla_admin,
    texto,
)
from components.admin.constantes import OPCIONES_STOCK
from components.admin.formato import dinero
from components.forms import (
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    numero_orquidea,
    selector_orquidea,
)
from components.shared import en_oferta, estado_cargando, precio_con_descuento
from state.cliente_api import ErrorApi

LIMITE = 100

COLUMNAS_PRODUCTOS = (
    {"name": "nombre", "label": "Producto", "field": "nombre", "align": "left"},
    {"name": "sku", "label": "SKU", "field": "sku", "align": "left"},
    {"name": "categoria", "label": "Categoría", "field": "categoria_nombre", "align": "left"},
    {"name": "sector", "label": "Sector", "field": "sector", "align": "left"},
    {"name": "marca", "label": "Marca", "field": "marca", "align": "left"},
    {
        "name": "presentacion",
        "label": "Presentación",
        "field": "presentacion",
        "align": "left",
    },
    {"name": "oferta", "label": "Oferta", "field": "oferta", "align": "left"},
    {
        "name": "precio_caja_oferta",
        "label": "Precio caja oferta",
        "field": "precio_caja_oferta",
        "align": "right",
    },
    {
        "name": "precio_unidad_oferta",
        "label": "Precio unidad oferta",
        "field": "precio_unidad_oferta",
        "align": "right",
    },
    {
        "name": "precio_caja",
        "label": "Precio caja",
        "field": "precio_caja",
        "align": "right",
        "dinero": True,
    },
    {
        "name": "precio_unidad",
        "label": "Precio unidad",
        "field": "precio_unidad",
        "align": "right",
        "dinero": True,
    },
    {
        "name": "existencias",
        "label": "Existencias",
        "field": "existencias",
        "align": "right",
    },
    {
        "name": "minimo",
        "label": "Mínimo",
        "field": "stock_minimo",
        "align": "right",
    },
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
)

COLUMNAS_CATEGORIAS = (
    {"name": "nombre", "label": "Categoría", "field": "nombre", "align": "left"},
    {"name": "sector", "label": "Sector", "field": "sector", "align": "left"},
    {
        "name": "total",
        "label": "Productos",
        "field": "total_productos",
        "align": "right",
    },
)


def listar_productos(api: Any, filtros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/catalogo/productos", params=filtros)


def listar_categorias(api: Any, filtros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/catalogo/categorias", params=filtros)


def guardar_producto(
    api: Any, producto_id: int | None, datos: dict[str, Any]
) -> dict[str, Any]:
    if producto_id is None:
        return api.post("/api/v1/admin/catalogo/productos", json=datos)
    return api.put(f"/api/v1/admin/catalogo/productos/{producto_id}", json=datos)


def guardar_categoria(
    api: Any, categoria_id: int | None, datos: dict[str, Any]
) -> dict[str, Any]:
    if categoria_id is None:
        return api.post("/api/v1/admin/catalogo/categorias", json=datos)
    return api.put(f"/api/v1/admin/catalogo/categorias/{categoria_id}", json=datos)


def filtrar_stock(productos: list[dict[str, Any]], opcion: str) -> list[dict[str, Any]]:
    """Filtro elegido por la persona: el backend no expone este parámetro."""
    if opcion == "con":
        return [item for item in productos if numero(item.get("existencias")) > 0]
    if opcion == "sin":
        return [item for item in productos if numero(item.get("existencias")) == 0]
    if opcion == "bajo":
        return [
            item
            for item in productos
            if numero(item.get("existencias")) < numero(item.get("stock_minimo"))
        ]
    return productos


def _sector(valor: Any) -> str:
    clave = str(valor or "")
    return SECTORES_ADMIN.get(clave, clave or "—")


def _filas_productos(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filas = []
    for producto in items:
        fila = dict(producto)
        fila["sector"] = _sector(producto.get("sector"))
        fila["marca"] = str(producto.get("marca") or "").strip() or "—"
        fila["presentacion"] = str(producto.get("presentacion") or "").strip() or "—"
        descuento = producto.get("descuento_pct") or 0
        fila["oferta"] = (
            f"{descuento} %" if en_oferta(producto) else "—"
        )
        fila["precio_caja_oferta"] = precio_con_descuento(
            producto.get("precio_caja"), descuento
        )
        fila["precio_unidad_oferta"] = precio_con_descuento(
            producto.get("precio_unidad"), descuento
        )
        fila["estado"] = "Activo" if producto.get("estado_activo") else "Inactivo"
        filas.append(fila)
    return filas


def _decimal(valor: Any) -> str:
    if valor is None or str(valor).strip() == "":
        return "0"
    return str(valor)


@ui.page("/admin/catalogo")
async def pagina_catalogo_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Productos del catálogo", ruta_activa="/admin/catalogo")

    mensajes = ui.column().classes("w-full")
    editando: dict[str, Any] = {"id": None}
    categorias: dict[int, str] = {}
    seleccion: dict[str, Any] = {"id": None}

    with ui.row().classes("w-full items-end gap-3"):
        busqueda = campo_orquidea("Buscar producto")
        sector = selector_orquidea(
            "Sector", {"": "Todos", **SECTORES_ADMIN}, value="", buscar=False
        )
        stock = selector_orquidea("Stock", OPCIONES_STOCK, value="", buscar=False)
        categoria_filtro = selector_orquidea("Categoría", {}, buscar=True)
        boton_orquidea("Buscar", lambda: cargar())

    with ui.element("section").classes("orq-admin-bloque w-full"):
        ui.label("Alta y edición de productos").classes("orq-tabla-titulo")
        ui.label("La categoría define el sector donde se ve el producto.").classes(
            "orq-bloque-ayuda"
        )
        with ui.row().classes("w-full items-end gap-3"):
            nombre = campo_orquidea("Nombre")
            sku = campo_orquidea("SKU")
            categoria_form = selector_orquidea("Categoría del producto", {}, buscar=True)
        with ui.row().classes("w-full items-end gap-3"):
            precio_caja = numero_orquidea("Precio por caja", moneda=True)
            precio_unidad = numero_orquidea("Precio por unidad", moneda=True)
            precio_media = numero_orquidea("Precio media caja", moneda=True)
            existencias = numero_orquidea("Existencias")
        with ui.row().classes("w-full items-end gap-3"):
            codigo = campo_orquidea("Código de barras")
            descripcion = campo_orquidea("Descripción corta")
            unidades = numero_orquidea("Unidades por caja", value=1)
        with ui.row().classes("w-full items-end gap-3"):
            marca = campo_orquidea("Marca")
            presentacion = campo_orquidea("Presentación")
            descuento = numero_orquidea(
                "Descuento %", value=0, min=0, max=90, precision=2
            )
        with ui.row().classes("orq-admin-acciones w-full"):
            boton_orquidea("Guardar producto", lambda: guardar())
            boton_orquidea(
                "Nuevo producto", lambda: limpiar_formulario(), variante="secundario"
            )

    tabla_zone = ui.column().classes("w-full")
    with tabla_zone:
        estado_cargando(3)

    def cargar_categorias() -> None:
        try:
            respuesta = listar_categorias(cliente_admin(), {"limite": LIMITE})
        except Exception:
            return
        items = list(respuesta.get("items") or [])
        categorias.clear()
        categorias.update({int(item["id"]): str(item.get("nombre") or "") for item in items})
        categoria_form.options = categorias
        categoria_form.update()
        categoria_filtro.options = {"": "Todas", **categorias}
        categoria_filtro.update()

    def cargar() -> None:
        mensajes.clear()
        filtros: dict[str, Any] = {"limite": LIMITE}
        if str(busqueda.value or "").strip():
            filtros["busqueda"] = str(busqueda.value).strip()
        if sector.value:
            filtros["sector"] = sector.value
        if categoria_filtro.value:
            filtros["categoria_id"] = categoria_filtro.value
        try:
            respuesta = listar_productos(cliente_admin(), filtros)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar los productos. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        items = filtrar_stock(
            list(respuesta.get("items") or []), str(stock.value or "")
        )
        tabla_zone.clear()
        with tabla_zone:
            tabla_admin(
                list(COLUMNAS_PRODUCTOS),
                _filas_productos(items),
                mensaje_vacio="No hay productos con estos filtros.",
            )
            with ui.row().classes("orq-admin-acciones w-full"):
                elegido = selector_orquidea(
                    "Producto",
                    {int(item["id"]): str(item.get("nombre") or "") for item in items},
                    buscar=True,
                )
                boton_orquidea("Editar", lambda: editar(elegido.value))
        seleccion["elegido"] = None

    def limpiar_formulario() -> None:
        editando["id"] = None
        for campo in (nombre, sku, codigo, descripcion, marca, presentacion):
            campo.value = ""
        for campo in (precio_caja, precio_unidad, precio_media, existencias):
            campo.value = None
        unidades.value = 1
        descuento.value = 0
        categoria_form.value = None

    def editar(producto_id: Any) -> None:
        if producto_id is None:
            ui.notify("Elige un producto.", type="warning")
            return
        try:
            respuesta = listar_productos(
                cliente_admin(), {"limite": LIMITE, "solo_activos": False}
            )
        except Exception:
            ui.label("No pudimos cargar el producto. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        producto = next(
            (
                item
                for item in list(respuesta.get("items") or [])
                if int(item.get("id") or 0) == int(producto_id)
            ),
            None,
        )
        if producto is None:
            ui.notify("No encontramos ese producto.", type="warning")
            return
        editando["id"] = int(producto_id)
        nombre.value = str(producto.get("nombre") or "")
        sku.value = str(producto.get("sku") or "")
        codigo.value = str(producto.get("codigo_barras") or "")
        descripcion.value = str(producto.get("descripcion_corta") or "")
        marca.value = str(producto.get("marca") or "")
        presentacion.value = str(producto.get("presentacion") or "")
        descuento.value = numero(producto.get("descuento_pct"))
        precio_caja.value = numero(producto.get("precio_caja"))
        precio_unidad.value = numero(producto.get("precio_unidad"))
        precio_media.value = (
            numero(producto.get("precio_media_caja"))
            if producto.get("precio_media_caja") is not None
            else None
        )
        existencias.value = numero(producto.get("existencias"))
        unidades.value = int(producto.get("unidades_por_caja") or 1)
        categoria_form.value = producto.get("categoria_id")

    def guardar() -> None:
        mensajes.clear()
        if not nombre.value or not sku.value:
            ui.notify("Completa el nombre y el SKU.", type="warning")
            return
        if not categoria_form.value:
            ui.notify("Elige la categoría del producto.", type="warning")
            return
        datos: dict[str, Any] = {
            "categoria_id": int(categoria_form.value),
            "nombre": str(nombre.value),
            "sku": str(sku.value),
            "codigo_barras": str(codigo.value or "") or None,
            "descripcion_corta": str(descripcion.value or "") or None,
            "marca": str(marca.value or "").strip() or None,
            "presentacion": str(presentacion.value or "").strip() or None,
            "descuento_pct": _decimal(descuento.value),
            "precio_caja": _decimal(precio_caja.value),
            "precio_unidad": _decimal(precio_unidad.value),
            "precio_media_caja": (
                _decimal(precio_media.value)
                if precio_media.value not in (None, "")
                else None
            ),
            "unidades_por_caja": int(unidades.value or 1),
        }
        if editando["id"] is None:
            datos["existencias_iniciales"] = _decimal(existencias.value)
        else:
            datos["existencias"] = _decimal(existencias.value)
        try:
            guardar_producto(cliente_admin(), editando["id"], datos)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos guardar el producto. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        ui.notify("Producto guardado.")
        limpiar_formulario()
        cargar_categorias()
        cargar()

    cargar_categorias()
    cargar()


@ui.page("/admin/catalogo/categorias")
async def pagina_categorias_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Categorías del catálogo", ruta_activa="/admin/catalogo/categorias")

    mensajes = ui.column().classes("w-full")
    editando: dict[str, Any] = {"id": None}
    with ui.row().classes("w-full items-end gap-3"):
        busqueda = campo_orquidea("Buscar categoría")
        sector = selector_orquidea(
            "Sector", {"": "Todos", **SECTORES_ADMIN}, value="", buscar=False
        )
        boton_orquidea("Buscar", lambda: cargar())
    with ui.element("section").classes("orq-admin-bloque w-full"):
        ui.label("Alta y edición de categorías").classes("orq-tabla-titulo")
        with ui.row().classes("w-full items-end gap-3"):
            nombre = campo_orquidea("Nombre")
            sector_form = selector_orquidea("Sector", SECTORES_ADMIN, buscar=False)
        with ui.row().classes("orq-admin-acciones w-full"):
            boton_orquidea("Guardar categoría", lambda: guardar())
            boton_orquidea(
                "Nueva categoría", lambda: limpiar(), variante="secundario"
            )
    tabla_zone = ui.column().classes("w-full")
    with tabla_zone:
        estado_cargando(3)

    def cargar() -> None:
        mensajes.clear()
        filtros: dict[str, Any] = {"limite": LIMITE}
        if str(busqueda.value or "").strip():
            filtros["busqueda"] = str(busqueda.value).strip()
        if sector.value:
            filtros["sector"] = sector.value
        try:
            respuesta = listar_categorias(cliente_admin(), filtros)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar las categorías. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        items = list(respuesta.get("items") or [])
        filas = []
        for categoria in items:
            fila = dict(categoria)
            fila["sector"] = _sector(categoria.get("sector"))
            filas.append(fila)
        tabla_zone.clear()
        with tabla_zone:
            tabla_admin(
                list(COLUMNAS_CATEGORIAS),
                filas,
                mensaje_vacio="No hay categorías con estos filtros.",
            )
            with ui.row().classes("orq-admin-acciones w-full"):
                elegida = selector_orquidea(
                    "Categoría",
                    {int(item["id"]): str(item.get("nombre") or "") for item in items},
                    buscar=True,
                )
                boton_orquidea("Editar", lambda: editar(elegida.value))

    def limpiar() -> None:
        editando["id"] = None
        nombre.value = ""
        sector_form.value = None

    def editar(categoria_id: Any) -> None:
        if categoria_id is None:
            ui.notify("Elige una categoría.", type="warning")
            return
        try:
            respuesta = listar_categorias(cliente_admin(), {"limite": LIMITE})
        except Exception:
            ui.label("No pudimos cargar la categoría. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        categoria = next(
            (
                item
                for item in list(respuesta.get("items") or [])
                if int(item.get("id") or 0) == int(categoria_id)
            ),
            None,
        )
        if categoria is None:
            ui.notify("No encontramos esa categoría.", type="warning")
            return
        editando["id"] = int(categoria_id)
        nombre.value = str(categoria.get("nombre") or "")
        sector_form.value = categoria.get("sector")

    def guardar() -> None:
        mensajes.clear()
        if not nombre.value:
            ui.notify("Escribe el nombre de la categoría.", type="warning")
            return
        datos = {"nombre": str(nombre.value), "sector": sector_form.value or None}
        try:
            guardar_categoria(cliente_admin(), editando["id"], datos)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos guardar la categoría. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        ui.notify("Categoría guardada.")
        limpiar()
        cargar()

    cargar()


__all__ = [
    "filtrar_stock",
    "guardar_categoria",
    "guardar_producto",
    "listar_categorias",
    "listar_productos",
    "pagina_catalogo_admin",
    "pagina_categorias_admin",
]
