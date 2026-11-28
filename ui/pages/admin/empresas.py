"""Administración de empresas: filtros, detalle y cambio de estado; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    SECTORES_ADMIN,
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    fecha,
    montar_admin,
    tabla_admin,
    texto,
)
from components.admin.constantes import OPCIONES_ESTADO
from components.admin.formato import dinero
from components.forms import (
    boton_orquidea,
    campo_orquidea,
    confirmar_accion,
    mostrar_error,
    selector_orquidea,
)
from components.shared import estado_cargando
from state.cliente_api import ErrorApi

LIMITE = 20

COLUMNAS = (
    {"name": "nombre", "label": "Empresa", "field": "nombre_empresa", "align": "left"},
    {"name": "ruc", "label": "RUC", "field": "ruc", "align": "left"},
    {"name": "sector", "label": "Sector", "field": "sector", "align": "left"},
    {"name": "activo", "label": "Estado", "field": "estado", "align": "left"},
    {
        "name": "comprado",
        "label": "Total comprado",
        "field": "total_comprado",
        "align": "right",
        "dinero": True,
    },
    {
        "name": "ultima",
        "label": "Última compra",
        "field": "fecha_ultima_compra",
        "align": "left",
        "fecha": True,
    },
)

COLUMNAS_PRODUCTOS = (
    {"name": "nombre", "label": "Producto", "field": "nombre", "align": "left"},
    {"name": "sku", "label": "SKU", "field": "sku", "align": "left"},
    {"name": "unidades", "label": "Unidades", "field": "unidades", "align": "right"},
    {
        "name": "monto",
        "label": "Monto",
        "field": "monto",
        "align": "right",
        "dinero": True,
    },
)

COLUMNAS_FACTURAS = (
    {"name": "serie", "label": "Número", "field": "numero_serie", "align": "left"},
    {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "left", "fecha": True},
    {"name": "total", "label": "Total", "field": "total", "align": "right", "dinero": True},
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
)

COLUMNAS_PEDIDOS = (
    {"name": "id", "label": "Pedido", "field": "id", "align": "left"},
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
)


def listar_empresas(api: Any, filtros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/empresas", params=filtros)


def obtener_empresa(api: Any, empresa_id: int) -> dict[str, Any]:
    return api.get(f"/api/v1/admin/empresas/{empresa_id}")


def cambiar_estado(
    api: Any, empresa_id: int, activo: bool, motivo: str
) -> dict[str, Any]:
    return api.put(
        f"/api/v1/admin/empresas/{empresa_id}/estado",
        json={"activo": activo, "motivo": motivo or None},
    )


def _sector(valor: Any) -> str:
    clave = str(valor or "")
    return SECTORES_ADMIN.get(clave, clave or "—")


def _filas(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filas = []
    for empresa in items:
        fila = dict(empresa)
        fila["sector"] = _sector(empresa.get("sector"))
        fila["estado"] = "Activa" if empresa.get("activo") else "Suspendida"
        filas.append(fila)
    return filas


@ui.page("/admin/empresas")
async def pagina_empresas_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Empresas", ruta_activa="/admin/empresas")

    mensajes = ui.column().classes("w-full")
    desplazamiento = {"valor": 0}
    seleccion: dict[str, Any] = {"id": None, "nombre": "", "activo": None}
    opciones_empresas: dict[int, str] = {}

    with ui.row().classes("w-full items-end gap-3"):
        busqueda = campo_orquidea("Buscar empresa")
        sector = selector_orquidea(
            "Sector", {"": "Todos", **SECTORES_ADMIN}, value="", buscar=False
        )
        activo = selector_orquidea("Estado", OPCIONES_ESTADO, value="", buscar=False)
        boton_orquidea("Buscar", lambda: _buscar())

    tabla_zone = ui.column().classes("w-full")
    paginacion = ui.row().classes("orq-paginacion w-full")
    with paginacion:
        resumen = ui.label().classes("orq-resumen")
        boton_anterior = boton_orquidea("Anterior", lambda: _mover(-LIMITE), variante="texto")
        boton_siguiente = boton_orquidea("Siguiente", lambda: _mover(LIMITE), variante="texto")

    with ui.row().classes("orq-admin-acciones w-full items-end"):
        elegida = selector_orquidea("Empresa", {}, buscar=True)
        motivo = campo_orquidea("Motivo del cambio", placeholder="Opcional")
        boton_orquidea("Ver detalle", lambda: _ver_detalle())
        boton_orquidea("Suspender", lambda: _confirmar_estado(False))
        boton_orquidea("Activar", lambda: _confirmar_estado(True), variante="secundario")

    detalle_zone = ui.column().classes("w-full")
    with tabla_zone:
        estado_cargando(3)

    def _filtros() -> dict[str, Any]:
        filtros: dict[str, Any] = {"desplazamiento": desplazamiento["valor"], "limite": LIMITE}
        if str(busqueda.value or "").strip():
            filtros["busqueda"] = str(busqueda.value).strip()
        if sector.value:
            filtros["sector"] = sector.value
        if activo.value:
            filtros["activo"] = activo.value == "true"
        return filtros

    def cargar() -> None:
        mensajes.clear()
        tabla_zone.clear()
        try:
            respuesta = listar_empresas(cliente_admin(), _filtros())
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar las empresas. Inténtalo de nuevo.").classes(
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
        opciones_empresas.clear()
        opciones_empresas.update(
            {int(item["id"]): str(item.get("nombre_empresa") or "") for item in items}
        )
        elegida.options = opciones_empresas
        elegida.update()

        with tabla_zone:
            tabla_admin(
                list(COLUMNAS),
                _filas(items),
                mensaje_vacio="No hay empresas con estos filtros.",
            )

    def _buscar() -> None:
        desplazamiento["valor"] = 0
        cargar()

    def _mover(delta: int) -> None:
        desplazamiento["valor"] = max(0, desplazamiento["valor"] + delta)
        cargar()

    def _elegir() -> bool:
        if elegida.value is None:
            ui.notify("Elige una empresa.", type="warning")
            return False
        empresa = next(
            (
                item
                for item in (elegida.options or {}).items()
                if item[0] == elegida.value
            ),
            None,
        )
        seleccion["id"] = int(elegida.value)
        seleccion["nombre"] = str(empresa[1]) if empresa else ""
        return True

    def _ver_detalle() -> None:
        if not _elegir():
            return
        detalle_zone.clear()
        try:
            detalle = obtener_empresa(cliente_admin(), int(seleccion["id"]))
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
                ui.label(
                    f"{texto(detalle.get('nombre_empresa'))} · {texto(detalle.get('ruc'))}"
                ).classes("orq-titulo")
                ui.label(
                    f"Sector: {_sector(detalle.get('sector'))} · "
                    f"Registro: {fecha(detalle.get('fecha_registro'))}"
                ).classes("orq-bloque-ayuda")
                ui.label(
                    f"Correo: {texto(detalle.get('email_contacto'))} · "
                    f"Teléfono: {texto(detalle.get('telefono'))} · "
                    f"Sucursal: {texto(detalle.get('sucursal'))}"
                ).classes("orq-bloque-ayuda")
                ui.label(
                    f"Ingresos: {dinero(detalle.get('ingresos'))} · "
                    f"Pedidos: {texto(detalle.get('pedidos_totales'))} · "
                    f"Facturas: {texto(detalle.get('facturas_totales'))}"
                ).classes("orq-bloque-ayuda")
                tabla_admin(
                    list(COLUMNAS_PRODUCTOS),
                    list(detalle.get("productos_mas_comprados") or []),
                    row_key="producto_id",
                    titulo="Productos más comprados",
                )
                tabla_admin(
                    list(COLUMNAS_FACTURAS),
                    list(detalle.get("ultimas_facturas") or []),
                    titulo="Últimas facturas",
                )
                tabla_admin(
                    list(COLUMNAS_PEDIDOS),
                    list(detalle.get("ultimos_pedidos") or []),
                    titulo="Últimos pedidos",
                )

    def _confirmar_estado(activo: bool) -> None:
        if not _elegir():
            return
        verbo = "Activar" if activo else "Suspender"
        confirmar_accion(
            f"{verbo} empresa",
            f"¿{verbo.lower()} el acceso de {seleccion['nombre']}?",
            lambda: _cambiar_estado(activo),
            etiqueta_confirmar=verbo,
            peligro=not activo,
        )

    def _cambiar_estado(activo: bool) -> None:
        mensajes.clear()
        try:
            cambiar_estado(
                cliente_admin(), int(seleccion["id"]), activo, str(motivo.value or "")
            )
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cambiar el estado. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        ui.notify("Empresa actualizada.")
        cargar()
        _ver_detalle()

    cargar()


__all__ = ["cambiar_estado", "listar_empresas", "obtener_empresa", "pagina_empresas_admin"]
