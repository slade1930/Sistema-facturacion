"""Gráficos propios del administrador con ui.echart; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin.formato import numero, texto
from components.shared import estado_vacio

COLOR_PRINCIPAL = "#6C2BD9"
COLOR_PROYECCION = "#A30F61"


def _opciones(
    etiquetas: list[str],
    series: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "backgroundColor": "transparent",
        "animationDuration": 300,
        "grid": {"left": 60, "right": 20, "top": 48, "bottom": 48},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 8, "textStyle": {"color": "#220A3A"}},
        "xAxis": {
            "type": "category",
            "data": etiquetas,
            "axisLabel": {"color": "#220A3A", "rotate": 30},
            "axisLine": {"lineStyle": {"color": "#E4D6FA"}},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {"color": "#220A3A"},
            "splitLine": {"lineStyle": {"color": "#E4D6FA"}},
        },
        "series": series,
    }


def _serie(nombre: str, valores: list[float | None], color: str) -> dict[str, Any]:
    return {
        "name": nombre,
        "type": "bar",
        "data": valores,
        "barMaxWidth": 28,
        "itemStyle": {"color": color},
    }


def grafico_ingresos(
    ingresos: dict[str, Any], pronostico: dict[str, Any] | None = None
) -> Any | None:
    """Barras mensuales reales y, si hay modelo, la proyección del ML."""
    por_mes = list(ingresos.get("por_mes") or [])
    if not por_mes:
        estado_vacio("Todavía no hay ingresos para graficar.")
        return None

    etiquetas = [texto(fila.get("mes")) for fila in por_mes]
    reales: list[float | None] = [numero(fila.get("ingresos")) for fila in por_mes]
    series = [_serie("Ingresos", reales, COLOR_PRINCIPAL)]

    if pronostico and pronostico.get("evaluado"):
        resultado = pronostico.get("resultado") or {}
        periodos = [texto(periodo) for periodo in resultado.get("periodos") or []]
        valores = [numero(valor) for valor in resultado.get("valores") or []]
        proyectados: list[float | None] = [None] * len(etiquetas)
        for periodo, valor in zip(periodos, valores):
            if periodo not in etiquetas:
                etiquetas.append(periodo)
                reales.append(None)
            proyectados.append(valor)
        while len(proyectados) < len(etiquetas):
            proyectados.append(None)
        series.append(_serie("Proyección", proyectados, COLOR_PROYECCION))

    return ui.echart(_opciones(etiquetas, series)).classes("orq-admin-grafico")


def grafico_grupos(
    filas: list[dict[str, Any]], *, titulo: str, clave_nombre: str = "nombre"
) -> Any | None:
    """Barras por empresa, sector o categoría con los datos del backend."""
    if not filas:
        estado_vacio(f"Todavía no hay datos de {titulo.lower()}.")
        return None
    etiquetas = [texto(fila.get(clave_nombre)) for fila in filas]
    valores = [numero(fila.get("ingresos")) for fila in filas]
    return ui.echart(
        _opciones(etiquetas, [_serie("Ingresos", valores, COLOR_PRINCIPAL)])
    ).classes("orq-admin-grafico")


__all__ = ["grafico_grupos", "grafico_ingresos"]
