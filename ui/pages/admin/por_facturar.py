"""Pedidos pendientes de factura para el administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    montar_admin,
    tabla_admin,
    texto,
)
from components.forms import boton_orquidea, mostrar_error, numero_orquidea, selector_orquidea
from components.shared import estado_cargando
from state.cliente_api import ErrorApi

LIMITE = 500

COLUMNAS = (
    {"name": "id", "label": "Pedido", "field": "id", "align": "left"},
    {"name": "empresa", "label": "Empresa", "field": "nombre_empresa", "align": "left"},
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
    {
        "name": "total",
        "label": "Total estimado",
        "field": "total_estimado",
        "align": "right",
        "dinero": True,
    },
    {
        "name": "creacion",
        "label": "Creado",
        "field": "fecha_creacion",
        "align": "left",
        "fecha": True,
    },
    {"name": "notas", "label": "Notas", "field": "notas", "align": "left"},
)

COLUMNAS_LINEAS = (
    {"name": "producto", "label": "Producto", "field": "producto_id", "align": "left"},
    {"name": "empaque", "label": "Empaque", "field": "tipo_empaque", "align": "left"},
    {"name": "cantidad", "label": "Cantidad", "field": "cantidad", "align": "right"},
    {"name": "subtotal", "label": "Subtotal", "field": "subtotal", "align": "right", "dinero": True},
)


def listar_por_facturar(api: Any, limite: int = LIMITE) -> list[dict[str, Any]]:
    respuesta = api.get(
        "/api/v1/admin/pedidos/por-facturar", params={"limite": limite}
    )
    return list(respuesta or [])


@ui.page("/admin/pedidos/por-facturar")
async def pagina_por_facturar_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Pedidos por facturar", ruta_activa="/admin/pedidos/por-facturar")

    mensajes = ui.column().classes("w-full")
    opciones: dict[int, str] = {}
    actual: dict[str, Any] = {"pedidos": []}

    with ui.row().classes("w-full items-end gap-3"):
        limite = numero_orquidea("Límite", value=LIMITE)
        boton_orquidea("Actualizar", lambda: cargar())

    tabla_zone = ui.column().classes("w-full")
    with tabla_zone:
        estado_cargando(3)
    with ui.row().classes("orq-admin-acciones w-full items-end"):
        elegido = selector_orquidea("Pedido", {}, buscar=True)
        boton_orquidea("Ver líneas", lambda: ver_lineas())
    detalle_zone = ui.column().classes("w-full")

    def cargar() -> None:
        mensajes.clear()
        tope = max(1, min(int(limite.value or LIMITE), LIMITE))
        try:
            pedidos = listar_por_facturar(cliente_admin(), tope)
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar los pedidos. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        actual["pedidos"] = pedidos
        opciones.clear()
        opciones.update({int(item["id"]): f"Pedido #{item['id']}" for item in pedidos})
        elegido.options = opciones
        elegido.update()
        tabla_zone.clear()
        with tabla_zone:
            tabla_admin(
                list(COLUMNAS),
                pedidos,
                mensaje_vacio="No hay pedidos pendientes de factura.",
            )
            if pedidos:
                with ui.row().classes("orq-admin-acciones w-full"):
                    for pedido in pedidos:
                        ui.link(
                            f"Facturar pedido #{pedido.get('id')}",
                            f"/pedidos/convertir-a-factura?pedido_id={pedido.get('id')}",
                        ).classes("orq-boton orq-boton--texto")

    def ver_lineas() -> None:
        if elegido.value is None:
            ui.notify("Elige un pedido.", type="warning")
            return
        pedido = next(
            (
                item
                for item in actual["pedidos"]
                if int(item.get("id") or 0) == int(elegido.value)
            ),
            None,
        )
        if pedido is None:
            ui.notify("No encontramos ese pedido.", type="warning")
            return
        detalle_zone.clear()
        with detalle_zone:
            tabla_admin(
                list(COLUMNAS_LINEAS),
                list(pedido.get("lineas") or []),
                row_key="producto_id",
                titulo=f"Líneas del pedido #{texto(pedido.get('id'))}",
                mensaje_vacio="Este pedido no tiene líneas.",
            )

    cargar()


__all__ = ["listar_por_facturar", "pagina_por_facturar_admin"]
