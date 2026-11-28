from typing import Any

from nicegui import ui

ESTADOS = {
    "emitida": "Emitida",
    "anulada": "Anulada",
    "en_revision": "En revisión",
    "pendiente": "Pendiente",
}


def tabla_orquidea(
    columnas: list[dict[str, Any]],
    filas: list[dict[str, Any]],
    *,
    row_key: str = "id",
    titulo: str | None = None,
) -> Any:
    """Tabla plana en escritorio y lista apilada en móvil."""
    columnas_limp = [dict(columna) for columna in columnas]
    filas_limp = [dict(fila) for fila in filas]

    if titulo:
        ui.label(titulo).classes("orq-tabla-titulo")

    tabla = (
        ui.table(columns=columnas_limp, rows=filas_limp, row_key=row_key)
        .props("sticky-header")
        .classes("orq-tabla w-full")
    )

    with ui.element("div").classes("orq-lista-movil w-full") as lista:
        for fila in filas_limp:
            with ui.element("article").classes("orq-fila-movil"):
                for columna in columnas_limp:
                    campo = str(columna.get("field", ""))
                    valor = fila.get(campo)
                    if campo == "estado" and isinstance(valor, str):
                        texto = ESTADOS.get(valor, valor.capitalize())
                    else:
                        texto = "" if valor is None else str(valor)
                    with ui.row().classes("orq-fila-dato w-full"):
                        ui.label(str(columna.get("label", ""))).classes(
                            "orq-fila-etiqueta"
                        )
                        clase_valor = "orq-fila-valor"
                        if columna.get("align") == "right":
                            clase_valor += " orq-fila-valor--derecha"
                        ui.label(texto).classes(clase_valor)
    return tabla


__all__ = ["tabla_orquidea"]
