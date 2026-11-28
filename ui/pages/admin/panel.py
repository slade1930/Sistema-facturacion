"""Panel global de métricas del administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    fecha,
    grafico_grupos,
    grafico_ingresos,
    montar_admin,
    rango_periodo,
    tabla_admin,
    tarjetas_admin,
    texto,
)
from components.admin.formato import dinero
from components.forms import mostrar_error, selector_orquidea
from components.shared import estado_cargando, estado_vacio
from state.cliente_api import ErrorApi

PERIODOS = {
    "todo": "Todo el tiempo",
    "30": "Últimos 30 días",
    "90": "Últimos 90 días",
    "anio": "Este año",
}

COLUMNAS_RANKING = (
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
    {"name": "pedidos", "label": "Pedidos", "field": "pedidos", "align": "right"},
)


def consultar_resumen(api: Any, parametros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/panel/resumen", params=parametros)


def consultar_ingresos(api: Any, parametros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/panel/ingresos", params=parametros)


def consultar_productos(api: Any, parametros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/panel/productos", params=parametros)


def consultar_pronostico(api: Any, parametros: dict[str, Any]) -> dict[str, Any]:
    """El panel llama directamente al endpoint de ML; no recalcula nada."""
    return api.get("/api/v1/ml/pronostico", params=parametros)


def listar_en_revision(api: Any) -> list[dict[str, Any]]:
    respuesta = api.get(
        "/api/v1/historial", params={"estado": "en_revision", "limite": 5}
    )
    if isinstance(respuesta, dict):
        return list(respuesta.get("items") or [])
    return list(respuesta or [])


def evaluar_anomalia(api: Any, factura_id: int) -> dict[str, Any]:
    """El panel pide la evaluación al endpoint de ML; no duplica el modelo."""
    respuesta = api.post(f"/api/v1/ml/anomalias/evaluar/{factura_id}")
    return respuesta if isinstance(respuesta, dict) else {}


def _parametros(clave_periodo: str) -> dict[str, Any]:
    desde, hasta = rango_periodo(clave_periodo)
    parametros: dict[str, Any] = {}
    if desde is not None:
        parametros["desde"] = desde.isoformat()
    if hasta is not None:
        parametros["hasta"] = hasta.isoformat()
    return parametros


def _estado_anomalia(evaluacion: dict[str, Any]) -> str:
    if not evaluacion.get("evaluado"):
        return "sin evaluar"
    resultado = evaluacion.get("resultado") or {}
    if resultado.get("en_revision"):
        return "En revisión"
    return "No sugiere revisión"


async def _construir_panel() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Panel de control", ruta_activa="/admin/panel")

    mensajes = ui.column().classes("w-full")
    with ui.row().classes("orq-admin-acciones"):
        periodo = selector_orquidea(
            "Período", PERIODOS, value="todo", buscar=False
        )

    resumen_zone = ui.column().classes("w-full")
    ingresos_zone = ui.column().classes("w-full")
    grupos_zone = ui.element("div").classes("orq-admin-dos w-full")
    ranking_zone = ui.column().classes("w-full")
    anomalias_zone = ui.column().classes("w-full")
    with resumen_zone:
        estado_cargando(3)

    def cargar() -> None:
        parametros = _parametros(str(periodo.value or "todo"))
        api = cliente_admin()
        mensajes.clear()
        resumen_zone.clear()
        ingresos_zone.clear()
        grupos_zone.clear()
        ranking_zone.clear()
        anomalias_zone.clear()

        try:
            resumen = consultar_resumen(api, parametros)
            ingresos = consultar_ingresos(api, parametros)
            productos = consultar_productos(api, parametros)
            pronostico = consultar_pronostico(api, {"meses": 6})
            facturas = listar_en_revision(api)
        except ErrorApi as error:
            with resumen_zone:
                estado_vacio("No pudimos cargar el panel.")
            mostrar_error(mensajes, error)
            return
        except Exception:
            with resumen_zone:
                estado_vacio("No pudimos cargar el panel. Inténtalo de nuevo.")
            return

        with resumen_zone:
            tarjetas_admin(resumen)
            ui.label(
                f"Datos del {fecha(resumen.get('desde'))} al {fecha(resumen.get('hasta'))}"
            ).classes("orq-admin-nota")

        with ui.element("section").classes("orq-admin-bloque w-full"):
            ui.label("Ingresos por mes").classes("orq-tabla-titulo")
            with ingresos_zone:
                grafico_ingresos(ingresos, pronostico)
                if not pronostico or not pronostico.get("evaluado"):
                    ui.label("Proyección: sin evaluar").classes("orq-admin-nota")

        with grupos_zone:
            for titulo, clave in (
                ("Ingresos por empresa", "por_empresa"),
                ("Ingresos por sector", "por_sector"),
                ("Ingresos por categoría", "por_categoria"),
            ):
                with ui.element("section").classes("w-full"):
                    ui.label(titulo).classes("orq-tabla-titulo")
                    filas = list(ingresos.get(clave) or [])
                    grafico_grupos(filas, titulo=titulo)

        with ranking_zone:
            for titulo, clave in (
                ("Más pedidos por unidades", "mas_pedidos_por_unidades"),
                ("Más pedidos por monto", "mas_pedidos_por_monto"),
                ("Menos pedidos", "menos_pedidos"),
            ):
                with ui.element("section").classes("orq-admin-bloque w-full"):
                    tabla_admin(
                        list(COLUMNAS_RANKING),
                        list(productos.get(clave) or []),
                        row_key="producto_id",
                        titulo=titulo,
                        mensaje_vacio="Todavía no hay productos para este ranking.",
                    )

        with anomalias_zone:
            with ui.element("section").classes("orq-admin-bloque w-full"):
                ui.label("Anomalías sugeridas por el modelo").classes(
                    "orq-tabla-titulo"
                )
                if not facturas:
                    estado_vacio("No hay facturas en revisión.")
                else:
                    for factura in facturas:
                        try:
                            evaluacion = evaluar_anomalia(
                                api, int(factura.get("id") or 0)
                            )
                        except Exception:
                            evaluacion = {}
                        estado = _estado_anomalia(evaluacion)
                        resultado = evaluacion.get("resultado") or {}
                        motive = texto(resultado.get("motivo_anomalia"))
                        with ui.element("article").classes("orq-admin-alerta w-full"):
                            ui.label(
                                f"{texto(factura.get('numero_serie'))} · "
                                f"{dinero(factura.get('total'))}"
                            ).classes("orq-dato-valor")
                            ui.label(f"Estado: {estado}").classes("orq-bloque-ayuda")
                            if estado != "sin evaluar":
                                ui.label(motive).classes("orq-bloque-ayuda")

    periodo.on_value_change(lambda evento: cargar())
    cargar()


@ui.page("/admin/panel")
async def pagina_panel() -> None:
    await _construir_panel()


@ui.page("/admin")
async def pagina_admin() -> None:
    await _construir_panel()


__all__ = [
    "pagina_admin",
    "consultar_ingresos",
    "consultar_productos",
    "consultar_pronostico",
    "consultar_resumen",
    "evaluar_anomalia",
    "listar_en_revision",
    "pagina_panel",
]
