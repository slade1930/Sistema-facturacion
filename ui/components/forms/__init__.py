from typing import Any, Callable

from nicegui import ui


def boton_orquidea(
    texto: str,
    on_click: Callable[[], Any] | None = None,
    *,
    variante: str = "primario",
    **kwargs: Any,
) -> Any:
    return ui.button(texto, on_click=on_click, **kwargs).classes(
        f"orq-boton orq-boton--{variante}"
    )


def campo_orquidea(etiqueta: str, **kwargs: Any) -> Any:
    clases = kwargs.pop("classes", "")
    return ui.input(etiqueta, **kwargs).classes(f"orq-campo {clases}".strip())


def mensaje_error(texto: str) -> Any:
    return ui.label(texto).classes("orq-error")


def notificar(mensaje: str, tipo: str = "positive") -> None:
    ui.notify(mensaje, type=tipo)


def esqueleto(alto: int = 16, ancho: str = "100%") -> Any:
    return ui.html(
        f'<div class="orq-esqueleto" style="height:{alto}px;width:{ancho}"></div>'
    )
