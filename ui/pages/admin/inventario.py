"""Inventario global, alertas y movimientos del administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    SECTORES_ADMIN,
    TIPOS_MOVIMIENTO_ADMIN,
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    fecha,
    montar_admin,
    numero,
    tabla_admin,
    texto,
)
from components.forms import (
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    numero_orquidea,
    selector_orquidea,
)
from components.shared import estado_cargando, estado_vacio
from state.cliente_api import ErrorApi

LIMITE = 100

COLUMNAS_INVENTARIO = (
    {"name": "producto", "label": "Producto", "field": "nombre_producto", "align": "left"},
    {"name": "sku", "label": "SKU", "field": "sku", "align": "left"},
    {
        "name": "existencias",
        "label": "Existencias",
        "field": "existencias",
        "align": "right",
    },
    {"name": "minimo", "label": "Mínimo", "field": "stock_minimo", "align": "right"},
    {
        "name": "actualizado",
        "label": "Actualizado",
        "field": "actualizado_en",
        "align": "left",
        "fecha": True,
    },
)

COLUMNAS_MOVIMIENTOS = (
    {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "left", "fecha": True},
    {"name": "producto", "label": "Producto", "field": "nombre_producto", "align": "left"},
    {"name": "tipo", "label": "Tipo", "field": "tipo", "align": "left"},
    {"name": "cantidad", "label": "Cantidad", "field": "cantidad", "align": "right"},
    {"name": "motivo", "label": "Motivo", "field": "motivo", "align": "left"},
)


def listar_inventario(api: Any, parametros: dict[str, Any]) -> list[dict[str, Any]]:
    respuesta = api.get("/api/v1/admin/inventario", params=parametros)
    return list(respuesta or [])


def listar_movimientos(api: Any, filtros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/inventario/movimientos", params=filtros)


def ajustar_inventario(
    api: Any, producto_id: int, datos: dict[str, Any]
) -> dict[str, Any]:
    return api.put(f"/api/v1/admin/inventario/{producto_id}", json=datos)


def bajo_minimo(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Señala las filas que el propio backend entregó por debajo del mínimo."""
    return [
        item
        for item in items
        if numero(item.get("existencias")) < numero(item.get("stock_minimo"))
    ]


def _tipo(valor: Any) -> str:
    clave = str(valor or "")
    return TIPOS_MOVIMIENTO_ADMIN.get(clave, clave or "—")


@ui.page("/admin/inventario")
async def pagina_inventario_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Inventario", ruta_activa="/admin/inventario")

    mensajes = ui.column().classes("w-full")
    inventario: dict[str, Any] = {}
    productos: dict[int, str] = {}

    with ui.row().classes("w-full items-end gap-3"):
        producto_filtro = selector_orquidea("Producto", {}, buscar=True)
        tipo_filtro = selector_orquidea(
            "Tipo de movimiento", {"": "Todos", **TIPOS_MOVIMIENTO_ADMIN}, value="", buscar=False
        )
        boton_orquidea("Aplicar filtros", lambda: cargar_movimientos())

    with ui.element("section").classes("orq-admin-bloque w-full"):
        ui.label("Ajustar existencias").classes("orq-tabla-titulo")
        with ui.row().classes("w-full items-end gap-3"):
            producto_ajuste = selector_orquidea("Producto a ajustar", {}, buscar=True)
            existencias = numero_orquidea("Existencias")
            minimo = numero_orquidea("Stock mínimo")
            motivo = campo_orquidea("Motivo", placeholder="Explica el ajuste")
        with ui.row().classes("orq-admin-acciones w-full"):
            boton_orquidea("Aplicar ajuste", lambda: guardar_ajuste())

    alertas_zone = ui.column().classes("w-full")
    tabla_zone = ui.column().classes("w-full")
    movimientos_zone = ui.column().classes("w-full")
    with tabla_zone:
        estado_cargando(3)

    def cargar_inventario() -> None:
        mensajes.clear()
        try:
            items = listar_inventario(cliente_admin(), {"limite": LIMITE})
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar el inventario. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        inventario.clear()
        inventario.update({int(item["producto_id"]): item for item in items})
        productos.clear()
        productos.update(
            {
                int(item["producto_id"]): str(item.get("nombre_producto") or "")
                for item in items
            }
        )
        producto_filtro.options = {"": "Todos", **productos}
        producto_filtro.update()
        producto_ajuste.options = productos
        producto_ajuste.update()

        alertas_zone.clear()
        with alertas_zone:
            ui.label("Alertas bajo el mínimo").classes("orq-tabla-titulo")
            alertas = bajo_minimo(items)
            if not alertas:
                estado_vacio("Ningún producto está bajo el mínimo.")
            else:
                for alerta in alertas:
                    with ui.element("article").classes("orq-admin-alerta w-full"):
                        ui.label(
                            f"{texto(alerta.get('nombre_producto'))} · "
                            f"{texto(alerta.get('existencias'))} / "
                            f"{texto(alerta.get('stock_minimo'))}"
                        ).classes("orq-dato-valor")
        tabla_zone.clear()
        with tabla_zone:
            tabla_admin(
                list(COLUMNAS_INVENTARIO),
                items,
                row_key="producto_id",
                mensaje_vacio="Todavía no hay existencias registradas.",
            )

    def cargar_movimientos() -> None:
        filtros: dict[str, Any] = {"limite": 20}
        if producto_filtro.value:
            filtros["producto_id"] = producto_filtro.value
        if tipo_filtro.value:
            filtros["tipo"] = tipo_filtro.value
        movimientos_zone.clear()
        with movimientos_zone:
            ui.label("Movimientos").classes("orq-tabla-titulo")
            try:
                respuesta = listar_movimientos(cliente_admin(), filtros)
            except ErrorApi as error:
                mostrar_error(mensajes, error)
                return
            except Exception:
                ui.label("No pudimos cargar los movimientos. Inténtalo de nuevo.").classes(
                    "orq-error"
                )
                return
            filas = []
            for movimiento in list(respuesta.get("items") or []):
                fila = dict(movimiento)
                fila["nombre_producto"] = productos.get(
                    int(movimiento.get("producto_id") or 0), "—"
                )
                fila["tipo"] = _tipo(movimiento.get("tipo"))
                filas.append(fila)
            tabla_admin(
                list(COLUMNAS_MOVIMIENTOS),
                filas,
                mensaje_vacio="No hay movimientos con estos filtros.",
            )

    def guardar_ajuste() -> None:
        mensajes.clear()
        if producto_ajuste.value is None:
            ui.notify("Elige un producto.", type="warning")
            return
        if not str(motivo.value or "").strip():
            ui.notify("Escribe el motivo del ajuste.", type="warning")
            return
        datos = {
            "existencias": str(existencias.value or 0),
            "stock_minimo": str(minimo.value or 0),
            "motivo": str(motivo.value).strip(),
        }
        try:
            ajustar_inventario(
                cliente_admin(), int(producto_ajuste.value), datos
            )
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos aplicar el ajuste. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        ui.notify("Ajuste aplicado.")
        motivo.value = ""
        cargar_inventario()
        cargar_movimientos()

    cargar_inventario()
    cargar_movimientos()


__all__ = [
    "ajustar_inventario",
    "bajo_minimo",
    "listar_inventario",
    "listar_movimientos",
    "pagina_inventario_admin",
]
