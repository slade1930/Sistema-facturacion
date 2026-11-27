from typing import Any

from nicegui import ui


def tabla_orquidea(
    columnas: list[dict[str, Any]],
    filas: list[dict[str, Any]],
    *,
    row_key: str = "id",
) -> Any:
    return ui.table(
        columns=list(columnas), rows=list(filas), row_key=row_key
    ).classes("orq-tabla w-full")
