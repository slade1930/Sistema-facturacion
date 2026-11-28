import asyncio
from typing import Any
from urllib.parse import quote

from nicegui import ui

from components.forms import (
    barra_acciones,
    campo_orquidea,
    mensaje_error,
    mostrar_error,
    seccion_formulario,
)
from components.layout import datos_negocio, montar_layout
from components.shared import estado_vacio
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


def _url_logo(ruta: str) -> str | None:
    texto = ruta.strip()
    if not texto or ".." in texto or "\\" in texto:
        return None
    if texto.startswith(("http://", "https://", "//")):
        return None
    nombre = texto.rsplit("/", 1)[-1]
    return f"/media/{quote(nombre)}" if nombre else None


def _pintar_logo(contenedor: Any, ruta: str) -> None:
    contenedor.clear()
    with contenedor:
        url = _url_logo(ruta)
        if url:
            ui.image(url).classes("orq-logo-vista w-28 h-24 object-contain")
        else:
            estado_vacio("Sin logo cargado")


def _sin_evaluar(datos: dict[str, Any]) -> bool:
    return datos.get("evaluado") is False or datos.get("modelo") is None


def _recomendaciones_pendientes(cliente_api: ClienteApi) -> bool:
    vistas = 0
    for ruta in ("/api/v1/ml/pronostico", "/api/v1/ml/recomendaciones"):
        try:
            respuesta = cliente_api.get(ruta)
        except Exception:
            continue
        if not isinstance(respuesta, dict):
            continue
        vistas += 1
        if not _sin_evaluar(respuesta):
            return False
    return vistas > 0


@ui.page("/configuracion")
def pagina_configuracion() -> None:
    montar_layout("Configuración del negocio", ruta_activa="/configuracion")

    mensajes = ui.column().classes("w-full gap-1")
    ui.label("Sistema en línea").classes("orq-ayuda")

    try:
        configuracion = obtener_configuracion(cliente)
    except Exception:
        with mensajes:
            mensaje_error(
                "No se pudieron cargar los datos del negocio. Intentá de nuevo."
            )
        return

    def guardar() -> None:
        mensajes.clear()
        valores = {clave: widget.value for clave, widget in campos.items()}
        try:
            datos = actualizar_configuracion(cliente, construir_cambios(valores))
        except ErrorApi as error:
            with mensajes:
                mensaje_error("No se pudo guardar. Revisá los datos e intentá de nuevo.")
            mostrar_error(mensajes, error)
            return
        except Exception:
            with mensajes:
                mensaje_error("No se pudo guardar. Revisá los datos e intentá de nuevo.")
            return
        mensajes.clear()
        with mensajes:
            ui.label("Configuración guardada.").classes("text-positive")
        datos_negocio.cache_clear()
        _pintar_logo(vista_logo, _valor(datos, "logo"))

    async def recibir_logo(event: Any) -> None:
        mensajes.clear()
        archivo = event.file
        contenido = await archivo.read()
        try:
            datos = await asyncio.to_thread(
                subir_logo, cliente, archivo.name, contenido, archivo.content_type
            )
        except ErrorApi as error:
            with mensajes:
                if error.status_code == 422:
                    mensaje_error(
                        "Revisá el archivo: debe ser PNG, JPG o WEBP "
                        "y pesar hasta 5 MB."
                    )
                else:
                    mensaje_error("No se pudo actualizar el logo. Intentá de nuevo.")
            return
        except Exception:
            with mensajes:
                mensaje_error("No se pudo actualizar el logo. Intentá de nuevo.")
            return
        with mensajes:
            ui.label("Logo actualizado.").classes("text-positive")
        datos_negocio.cache_clear()
        _pintar_logo(vista_logo, _valor(datos, "logo"))

    campos: dict[str, Any] = {}
    etiquetas = {clave: etiqueta for etiqueta, clave in CAMPOS_TEXTO}

    with seccion_formulario(
        "Datos del negocio", "Los datos que aparecen en cada factura."
    ):
        for clave in (
            "empresa_nombre",
            "empresa_ruc",
            "empresa_direccion",
            "empresa_correo",
            "empresa_telefono",
        ):
            campos[clave] = campo_orquidea(
                etiquetas[clave], value=_valor(configuracion, clave)
            ).classes("w-full")
        campos["mostrar_ruc"] = ui.checkbox(
            "Mostrar RUC", value=bool(configuracion.get("mostrar_ruc", True))
        )

    with seccion_formulario("Apariencia", "Tonos suaves para el documento."):
        for clave in ("color_principal", "color_barra_factura", "color_tabla"):
            campos[clave] = campo_orquidea(
                etiquetas[clave],
                value=_valor(configuracion, clave),
                placeholder="#3A0088",
            ).classes("w-full")

    with seccion_formulario(
        "Logo", "Una imagen sencilla para identificar al negocio.", rejilla=False
    ):
        with ui.element("div").classes("orq-dos-columnas w-full"):
            with ui.column().classes("w-full gap-1"):
                ui.upload(
                    label="Elegir imagen",
                    auto_upload=True,
                    max_file_size=5 * 1024 * 1024,
                    max_files=1,
                    on_upload=recibir_logo,
                ).classes("w-full")
                ui.label("PNG, JPG o WEBP · hasta 5 MB").classes("orq-ayuda")
            vista_logo = ui.column().classes("w-full items-start")
        _pintar_logo(vista_logo, _valor(configuracion, "logo"))

    with seccion_formulario(
        "Textos por defecto", "Notas que se agregan automáticamente."
    ):
        for clave in ("datos_bancarios", "notas_predeterminadas"):
            campos[clave] = campo_orquidea(
                etiquetas[clave], value=_valor(configuracion, clave)
            ).classes("w-full")

    if _recomendaciones_pendientes(cliente):
        with ui.element("section").classes("orq-seccion w-full"):
            ui.label("Recomendaciones automáticas").classes("orq-seccion-titulo")
            ui.label(
                "Sugerencias disponibles cuando haya suficiente historial."
            ).classes("orq-seccion-ayuda")
            estado_vacio("Sin evaluar")

    barra_acciones("Guardar", guardar, destino_cancelar="/")
