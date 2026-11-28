"""Consulta global de pedidos del administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    ESTADOS_PEDIDO_ADMIN,
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    montar_admin,
    tabla_admin,
    texto,
)
from components.forms import boton_orquidea, campo_orquidea, mostrar_error, selector_orquidea
from components.shared import estado_cargando
from state.cliente_api import ErrorApi

LIMITE = 20

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
    {
        "name": "factura",
        "label": "Factura",
        "field": "factura_generada_id",
        "align": "left",
    },
)

COLUMNAS_LINEAS = (
    {"name": "producto", "label": "Producto", "field": "producto_id", "align": "left"},
    {"name": "empaque", "label": "Empaque", "field": "tipo_empaque", "align": "left"},
    {"name": "cantidad", "label": "Cantidad", "field": "cantidad", "align": "right"},
    {"name": "subtotal", "label": "Subtotal", "field": "subtotal", "align": "right", "dinero": True},
)


def listar_pedidos(api: Any, filtros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/pedidos", params=filtros)


def obtener_pedido(api: Any, pedido_id: int) -> dict[str, Any]:
    return api.get(f"/api/v1/admin/pedidos/{pedido_id}")


def _estado(valor: Any) -> str:
    clave = str(valor or "")
    return ESTADOS_PEDIDO_ADMIN.get(clave, clave or "—")


def _filas(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filas = []
    for pedido in items:
        fila = dict(pedido)
        fila["estado"] = _estado(pedido.get("estado"))
        filas.append(fila)
    return filas


@ui.page("/admin/pedidos")
async def pagina_pedidos_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Todos los pedidos", ruta_activa="/admin/pedidos")

    mensajes = ui.column().classes("w-full")
    desplazamiento = {"valor": 0}
    opciones: dict[int, str] = {}

    with ui.row().classes("w-full items-end gap-3"):
        estado_filtro = selector_orquidea(
            "Estado", {"": "Todos", **ESTADOS_PEDIDO_ADMIN}, value="", buscar=False
        )
        empresa_filtro = campo_orquidea("ID de empresa")
        desde = campo_orquidea("Desde", placeholder="AAAA-MM-DD")
        hasta = campo_orquidea("Hasta", placeholder="AAAA-MM-DD")
        boton_orquidea("Buscar", lambda: _buscar())

    tabla_zone = ui.column().classes("w-full")
    paginacion = ui.row().classes("orq-paginacion w-full")
    with paginacion:
        resumen = ui.label().classes("orq-resumen")
        boton_anterior = boton_orquidea("Anterior", lambda: _mover(-LIMITE), variante="texto")
        boton_siguiente = boton_orquidea("Siguiente", lambda: _mover(LIMITE), variante="texto")

    with ui.row().classes("orq-admin-acciones w-full items-end"):
        elegido = selector_orquidea("Pedido", {}, buscar=True)
        boton_orquidea("Ver detalle", lambda: ver_detalle())

    detalle_zone = ui.column().classes("w-full")
    with tabla_zone:
        estado_cargando(3)

    def _filtros() -> dict[str, Any]:
        filtros: dict[str, Any] = {
            "desplazamiento": desplazamiento["valor"],
            "limite": LIMITE,
        }
        if estado_filtro.value:
            filtros["estado"] = estado_filtro.value
        if str(empresa_filtro.value or "").strip():
            filtros["empresa_id"] = int(empresa_filtro.value)
        if str(desde.value or "").strip():
            filtros["desde"] = str(desde.value).strip()
        if str(hasta.value or "").strip():
            filtros["hasta"] = str(hasta.value).strip()
        return filtros

    def cargar() -> None:
        mensajes.clear()
        try:
            respuesta = listar_pedidos(cliente_admin(), _filtros())
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar los pedidos. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        items = list(respuesta.get("items") or [])
        total = int(respuesta.get("total") or 0)
        inicio = int(respuesta.get("desplazamiento") or 0)
        fin = min(inicio + len(items), total)
        resumen.text = (
            f"Mostrando {inicio + 1}-{fin} de {total}" if items else "Sin resultados"
        )
        boton_anterior.set_visibility(inicio > 0)
        boton_siguiente.set_visibility(fin < total)
        opciones.clear()
        opciones.update({int(item["id"]): f"Pedido #{item['id']}" for item in items})
        elegido.options = opciones
        elegido.update()
        tabla_zone.clear()
        with tabla_zone:
            tabla_admin(
                list(COLUMNAS),
                _filas(items),
                mensaje_vacio="No hay pedidos con estos filtros.",
            )

    def _buscar() -> None:
        desplazamiento["valor"] = 0
        cargar()

    def _mover(delta: int) -> None:
        desplazamiento["valor"] = max(0, desplazamiento["valor"] + delta)
        cargar()

    def ver_detalle() -> None:
        if elegido.value is None:
            ui.notify("Elige un pedido.", type="warning")
            return
        detalle_zone.clear()
        try:
            pedido = obtener_pedido(cliente_admin(), int(elegido.value))
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar el detalle. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        with detalle_zone:
            with ui.element("section").classes("orq-admin-bloque w-full"):
                ui.label(f"Pedido #{texto(pedido.get('id'))}").classes("orq-titulo")
                ui.label(
                    f"Empresa: {texto(pedido.get('nombre_empresa'))} · "
                    f"Estado: {_estado(pedido.get('estado'))}"
                ).classes("orq-bloque-ayuda")
                ui.label(f"Notas: {texto(pedido.get('notas'))}").classes(
                    "orq-bloque-ayuda"
                )
                tabla_admin(
                    list(COLUMNAS_LINEAS),
                    list(pedido.get("lineas") or []),
                    mensaje_vacio="Este pedido no tiene líneas.",
                )

    cargar()


__all__ = ["listar_pedidos", "obtener_pedido", "pagina_pedidos_admin"]
