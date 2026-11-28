"""Tablas planas del administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin.formato import dinero, fecha, texto
from components.shared import estado_vacio


def _valor(fila: dict[str, Any], columna: dict[str, Any]) -> str:
    campo = str(columna.get("field") or "")
    dato = fila.get(campo)
    if dato is None or dato == "":
        return "—"
    if columna.get("dinero"):
        return dinero(dato)
    if columna.get("fecha"):
        return fecha(dato)
    return texto(dato)


def tabla_admin(
    columnas: list[dict[str, Any]],
    filas: list[dict[str, Any]],
    *,
    row_key: str = "id",
    titulo: str | None = None,
    mensaje_vacio: str = "Todavía no hay datos para mostrar.",
) -> Any | None:
    """Tabla en escritorio y lista apilada en móvil, sin quitarle datos al admin."""
    if titulo:
        ui.label(titulo).classes("orq-tabla-titulo")
    if not filas:
        estado_vacio(mensaje_vacio)
        return None

    columnas_limp = [
        {clave: valor for clave, valor in columna.items() if clave != "dinero" and clave != "fecha"}
        for columna in columnas
    ]
    visibles = []
    for indice, fila in enumerate(filas):
        visible = {
            str(columna.get("field") or ""): _valor(fila, columna)
            for columna in columnas
        }
        visible["_clave"] = str(fila.get(row_key) or indice)
        visibles.append(visible)

    tabla = (
        ui.table(columns=columnas_limp, rows=visibles, row_key="_clave")
        .props("sticky-header")
        .classes("orq-tabla orq-admin-tabla w-full")
    )

    with ui.element("div").classes("orq-lista-movil w-full"):
        for fila in visibles:
            with ui.element("article").classes("orq-fila-movil"):
                for columna in columnas_limp:
                    campo = str(columna.get("field") or "")
                    with ui.row().classes("orq-fila-dato w-full"):
                        ui.label(str(columna.get("label") or "")).classes(
                            "orq-fila-etiqueta"
                        )
                        clase = "orq-fila-valor"
                        if columna.get("align") == "right":
                            clase += " orq-fila-valor--derecha"
                        ui.label(fila.get(campo) or "—").classes(clase)
    return tabla


__all__ = ["tabla_admin"]
