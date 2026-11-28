from contextlib import contextmanager
from typing import Any, Callable, Iterator

from nicegui import ui

from state.cliente_api import ErrorApi

CAMPOS_AMIGABLES = {
    "cliente_nombre": "Cliente",
    "cliente_ruc": "RUC del cliente",
    "lineas": "Líneas",
    "numero_serie": "Número de serie",
    "codigo": "Código de verificación",
    "empresa_nombre": "Empresa",
    "empresa_ruc": "RUC",
    "pedido_id": "Pedido",
    "estado": "Estado",
    "cliente_id": "Cliente",
}

MENSAJES_AMIGABLES = {
    "Field required": "falta este dato",
    "List should have at least 1 item": "agregá al menos una línea",
    "none is not an allowed value": "elegí una opción",
    "value is not a valid decimal": "usá un número válido",
}


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


def boton_enlace(
    texto: str, destino: str, *, variante: str = "secundario"
) -> Any:
    return ui.link(texto, destino).classes(f"orq-boton orq-boton--{variante}")


def campo_orquidea(etiqueta: str, **kwargs: Any) -> Any:
    clases = kwargs.pop("classes", "")
    return ui.input(etiqueta, **kwargs).props("stack-label").classes(
        f"orq-campo {clases}".strip()
    )


def numero_orquidea(
    etiqueta: str, *, moneda: bool = False, **kwargs: Any
) -> Any:
    clases = kwargs.pop("classes", "")
    if moneda and "prefix" not in kwargs:
        kwargs["prefix"] = "$"
    return ui.number(label=etiqueta, **kwargs).props("stack-label").classes(
        f"orq-campo orq-campo--numero {clases}".strip()
    )


def selector_orquidea(
    etiqueta: str, opciones: list[Any] | dict[Any, str], *, buscar: bool = True, **kwargs: Any
) -> Any:
    clases = kwargs.pop("classes", "")
    selector = ui.select(
        opciones, label=etiqueta, with_input=buscar, **kwargs
    )
    return selector.props("stack-label").classes(f"orq-campo {clases}".strip())


@contextmanager
def seccion_formulario(
    titulo: str, ayuda: str | None = None, *, rejilla: bool = True
) -> Iterator[None]:
    with ui.element("section").classes("orq-seccion w-full"):
        ui.label(titulo).classes("orq-seccion-titulo")
        if ayuda:
            ui.label(ayuda).classes("orq-seccion-ayuda")
        if rejilla:
            with ui.element("div").classes("orq-rejilla w-full"):
                yield
        else:
            yield


def barra_acciones(
    principal: str,
    on_principal: Callable[[], Any] | None,
    *,
    destino_cancelar: str = "/",
    variante: str = "primario",
) -> Any:
    with ui.row().classes("orq-barra-acciones w-full") as barra:
        boton_orquidea(principal, on_principal, variante=variante)
        boton_enlace("Cancelar", destino_cancelar, variante="texto")
    return barra


def mensaje_error(texto: str) -> Any:
    return ui.label(texto).classes("orq-error")


def mostrar_error(contenedor: Any, error: Exception) -> None:
    """Explica el fallo sin mostrar códigos, rutas ni mensajes técnicos."""
    with contenedor:
        if not isinstance(error, ErrorApi):
            mensaje_error("No se pudo completar la acción. Intentá de nuevo.")
            return
        mensaje_error(error.detail)
        for detalle in error.errors:
            ubicacion = ""
            if isinstance(detalle, dict):
                partes = detalle.get("loc") or []
                if partes:
                    clave = str(partes[-1])
                    ubicacion = CAMPOS_AMIGABLES.get(clave, clave.replace("_", " "))
                mensaje = str(detalle.get("msg") or "").strip()
                texto = MENSAJES_AMIGABLES.get(mensaje, "")
                if not texto:
                    texto = mensaje if mensaje and mensaje[0].isupper() else "revisá este dato"
                mensaje_error(f"{ubicacion}: {texto}." if ubicacion else f"{texto}.")
            else:
                mensaje_error("Revisá los datos e intentá de nuevo.")


def notificar(mensaje: str, tipo: str = "positive") -> None:
    ui.notify(mensaje, type=tipo)


def confirmar_accion(
    titulo: str,
    texto: str,
    al_confirmar: Callable[[], Any],
    *,
    etiqueta_confirmar: str = "Confirmar",
    peligro: bool = True,
) -> Any:
    with ui.dialog() as dialogo, ui.card().classes("orq-confirmacion"):
        ui.label(titulo).classes("orq-confirmacion-titulo")
        ui.label(texto).classes("orq-confirmacion-texto")
        with ui.row().classes("orq-confirmacion-acciones w-full"):
            boton_orquidea("Cancelar", dialogo.close, variante="secundario")

            def aceptar() -> None:
                dialogo.close()
                al_confirmar()

            boton_orquidea(
                etiqueta_confirmar, aceptar, variante="peligro" if peligro else "primario"
            )
    dialogo.open()
    return dialogo


def esqueleto(alto: int = 16, ancho: str = "100%") -> Any:
    return ui.html(
        f'<div class="orq-esqueleto" style="height:{alto}px;width:{ancho}"></div>'
    )


__all__ = [
    "barra_acciones",
    "boton_enlace",
    "boton_orquidea",
    "campo_orquidea",
    "confirmar_accion",
    "esqueleto",
    "mensaje_error",
    "mostrar_error",
    "notificar",
    "numero_orquidea",
    "seccion_formulario",
    "selector_orquidea",
]
