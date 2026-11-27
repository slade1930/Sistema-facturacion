import asyncio
from typing import Any

from nicegui import ui

from components.layout import montar_layout
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()

CAMPOS_EDICION = (
    "empresa_nombre",
    "empresa_ruc",
    "mostrar_ruc",
    "empresa_direccion",
    "empresa_correo",
    "empresa_telefono",
    "color_principal",
    "color_barra_factura",
    "color_tabla",
    "datos_bancarios",
    "notas_predeterminadas",
)

CAMPOS_TEXTO = (
    ("Empresa", "empresa_nombre"),
    ("RUC", "empresa_ruc"),
    ("Dirección", "empresa_direccion"),
    ("Correo", "empresa_correo"),
    ("Teléfono", "empresa_telefono"),
    ("Color principal", "color_principal"),
    ("Color de barra de factura", "color_barra_factura"),
    ("Color de tabla", "color_tabla"),
    ("Datos bancarios", "datos_bancarios"),
    ("Notas predeterminadas", "notas_predeterminadas"),
)


def obtener_configuracion(cliente_api: ClienteApi) -> dict[str, Any]:
    return cliente_api.get("/api/v1/configuracion")


def construir_cambios(valores: dict[str, Any]) -> dict[str, Any]:
    cambios: dict[str, Any] = {}
    for clave in CAMPOS_EDICION:
        valor = valores.get(clave)
        if isinstance(valor, str):
            valor = valor.strip() or None
        cambios[clave] = valor
    return cambios


def actualizar_configuracion(
    cliente_api: ClienteApi, cambios: dict[str, Any]
) -> dict[str, Any]:
    return cliente_api.put("/api/v1/configuracion", json=cambios)


def subir_logo(
    cliente_api: ClienteApi,
    nombre: str,
    contenido: bytes,
    tipo_contenido: str,
) -> dict[str, Any]:
    return cliente_api.post(
        "/api/v1/configuracion/logo",
        files={"archivo": (nombre, contenido, tipo_contenido)},
    )


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


@ui.page("/configuracion")
def pagina_configuracion() -> None:
    montar_layout("Configuración")

    mensajes = ui.column()
    try:
        configuracion = obtener_configuracion(cliente)
    except ErrorApi as error:
        with mensajes:
            ui.label(f"{error.code}: {error.detail}").classes("text-negative")
        return

    campos: dict[str, Any] = {}
    with ui.card().classes("w-full gap-2"):
        ui.label("Datos del negocio").classes("text-h6")
        for etiqueta, clave in CAMPOS_TEXTO:
            campos[clave] = ui.input(
                etiqueta, value=_valor(configuracion, clave)
            ).classes("w-full")
        campos["mostrar_ruc"] = ui.checkbox(
            "Mostrar RUC", value=bool(configuracion.get("mostrar_ruc", True))
        )
        ruta_logo = ui.label(
            f"Logo actual: {_valor(configuracion, 'logo') or 'sin logo'}"
        ).classes("text-caption")

    def mostrar_error(error: ErrorApi) -> None:
        mensajes.clear()
        with mensajes:
            ui.label(f"{error.code}: {error.detail}").classes("text-negative")
            for item in error.errors:
                ui.label(str(item)).classes("text-caption text-negative")

    def guardar() -> None:
        valores = {clave: widget.value for clave, widget in campos.items()}
        try:
            datos = actualizar_configuracion(cliente, construir_cambios(valores))
        except ErrorApi as error:
            mostrar_error(error)
            return
        mensajes.clear()
        with mensajes:
            ui.label("Configuración guardada.").classes("text-positive")
        ruta_logo.set_text(f"Logo actual: {_valor(datos, 'logo') or 'sin logo'}")

    async def recibir_logo(event: Any) -> None:
        archivo = event.file
        contenido = await archivo.read()
        try:
            datos = await asyncio.to_thread(
                subir_logo, cliente, archivo.name, contenido, archivo.content_type
            )
        except ErrorApi as error:
            mostrar_error(error)
            return
        mensajes.clear()
        with mensajes:
            ui.label("Logo actualizado.").classes("text-positive")
        ruta_logo.set_text(f"Logo actual: {_valor(datos, 'logo') or 'sin logo'}")

    with ui.row().classes("gap-2 my-2"):
        ui.button("Guardar", on_click=guardar)
        ui.upload(
            label="Subir logo (PNG, JPG o WEBP, hasta 5 MB)",
            auto_upload=True,
            max_file_size=5 * 1024 * 1024,
            max_files=1,
            on_upload=recibir_logo,
        )
