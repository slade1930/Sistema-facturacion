import asyncio
from typing import Any
from urllib.parse import quote

import httpx
from nicegui import ui

from components.admin.seguridad import conectar_sesion, exigir_admin
from components.forms import (
    barra_acciones,
    boton_orquidea,
    campo_orquidea,
    mensaje_error,
    mostrar_error,
    notificar,
    seccion_formulario,
    texto_amigable,
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

MENSAJE_CONEXION = (
    "No pudimos conectar con el sistema. Revisa tu conexión e inténtalo de nuevo."
)
MENSAJE_CARGA = "No pudimos cargar los datos del negocio."
MENSAJE_GUARDADO = "Cambios guardados"
MENSAJE_SIN_CAMBIOS = "No hay cambios para guardar."
MENSAJE_REVISAR = "Revisa los datos marcados."
PRIMERA_CONFIGURACION = (
    "Aún no configuraste tu negocio. Completa los datos para empezar."
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


def cambios_para_guardar(
    configuracion: dict[str, Any],
    valores: dict[str, Any],
    *,
    inicial: bool = False,
) -> dict[str, Any]:
    """Envía todos los datos en la primera carga y solo lo cambiado después."""
    cambios = construir_cambios(valores)
    if inicial:
        return cambios
    return {
        clave: valor
        for clave, valor in cambios.items()
        if valor != _valor_normalizado(configuracion, clave)
    }


def _valor_normalizado(datos: dict[str, Any], clave: str) -> Any:
    valor = datos.get(clave)
    if isinstance(valor, str):
        return valor.strip() or None
    if isinstance(valor, bool):
        return valor
    return None


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


def es_error_de_conexion(error: Exception) -> bool:
    return isinstance(
        error,
        (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError),
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


def _etiquetas() -> dict[str, str]:
    return {clave: etiqueta for etiqueta, clave in CAMPOS_TEXTO}


def _errores_por_campo(error: ErrorApi) -> dict[str, str]:
    encontrados: dict[str, str] = {}
    for detalle in error.errors:
        if not isinstance(detalle, dict):
            continue
        partes = detalle.get("loc") or []
        if not partes:
            continue
        clave = str(partes[-1])
        if clave not in CAMPOS_EDICION:
            continue
        texto = texto_amigable(str(detalle.get("msg") or ""))
        encontrados[clave] = texto
    return encontrados


@ui.page("/configuracion")
async def pagina_configuracion() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_layout("Configuración del negocio", ruta_activa="/configuracion")

    mensajes = ui.column().classes("w-full gap-1")
    contenido = ui.column().classes("w-full gap-2")
    configuracion: dict[str, Any] = {}
    errores_campos: dict[str, Any] = {}

    def aviso_con_reintento(contenedor: Any, texto: str, accion: Any) -> None:
        with contenedor:
            mensaje_error(texto)
            boton_orquidea("Reintentar", accion, variante="secundario")
        notificar(texto, tipo="negative")

    def limpiar_errores_campos() -> None:
        for contenedor in errores_campos.values():
            contenedor.clear()

    def reintentar_guardado() -> None:
        guardar()

    def reintentar_carga() -> None:
        cargar()

    def mostrar_errores_campos(error: ErrorApi) -> None:
        etiquetas = _etiquetas()
        for clave, texto in _errores_por_campo(error).items():
            contenedor = errores_campos.get(clave)
            if contenedor is not None:
                with contenedor:
                    mensaje_error(f"{etiquetas.get(clave, clave)}: {texto}.")

    def confirmar_cambios(datos: dict[str, Any]) -> None:
        mensajes.clear()
        with mensajes:
            ui.label(MENSAJE_GUARDADO).classes("text-positive")
        notificar(MENSAJE_GUARDADO)
        datos_negocio.cache_clear()
        _pintar_logo(vista_logo, _valor(datos, "logo"))

    def guardar(*, notificar_cambio: bool = True) -> dict[str, Any] | None:
        mensajes.clear()
        limpiar_errores_campos()
        valores = {clave: widget.value for clave, widget in campos.items()}
        cambios = cambios_para_guardar(
            configuracion, valores, inicial=not configuracion
        )
        if not cambios:
            if notificar_cambio:
                with mensajes:
                    ui.label(MENSAJE_SIN_CAMBIOS).classes("orq-ayuda")
                notificar(MENSAJE_SIN_CAMBIOS, tipo="info")
            return None
        try:
            datos = actualizar_configuracion(cliente, cambios)
        except ErrorApi as error:
            with mensajes:
                mensaje_error(error.detail)
            mostrar_errores_campos(error)
            if _errores_por_campo(error):
                notificar(MENSAJE_REVISAR, tipo="warning")
            else:
                notificar(error.detail, tipo="negative")
            return None
        except Exception as error:
            if es_error_de_conexion(error):
                aviso_con_reintento(mensajes, MENSAJE_CONEXION, reintentar_guardado)
            else:
                aviso_con_reintento(mensajes, MENSAJE_CARGA, reintentar_guardado)
            return None
        configuracion.update(datos)
        if notificar_cambio:
            confirmar_cambios(datos)
        else:
            datos_negocio.cache_clear()
        return datos

    async def recibir_logo(event: Any) -> None:
        mensajes.clear()
        limpiar_errores_campos()
        archivo = event.file
        if not configuracion:
            if guardar(notificar_cambio=False) is None:
                return
        contenido = await archivo.read()
        try:
            datos = await asyncio.to_thread(
                subir_logo, cliente, archivo.name, contenido, archivo.content_type
            )
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            notificar(error.detail, tipo="negative")
            return
        except Exception as error:
            if es_error_de_conexion(error):
                aviso_con_reintento(mensajes, MENSAJE_CONEXION, lambda: ui.navigate.to("/configuracion"))
            else:
                aviso_con_reintento(mensajes, MENSAJE_CARGA, lambda: ui.navigate.to("/configuracion"))
            return
        configuracion.update(datos)
        confirmar_cambios(datos)

    def campo_edituable(
        clave: str, etiqueta: str, *, placeholder: str | None = None
    ) -> None:
        opciones: dict[str, Any] = {"value": _valor(configuracion, clave)}
        if placeholder:
            opciones["placeholder"] = placeholder
        campos[clave] = campo_orquidea(etiqueta, **opciones).classes("w-full")
        errores_campos[clave] = ui.column().classes("w-full gap-0")

    def montar_formulario(inicial: bool) -> None:
        nonlocal vista_logo
        campos.clear()
        errores_campos.clear()
        with contenido:
            if inicial:
                ui.label(PRIMERA_CONFIGURACION).classes("orq-bloque-ayuda")
            ui.label("Sistema en línea").classes("orq-ayuda")

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
                    campo_edituable(clave, _etiquetas()[clave])
                campos["mostrar_ruc"] = ui.checkbox(
                    "Mostrar RUC", value=bool(configuracion.get("mostrar_ruc", True))
                )
                errores_campos["mostrar_ruc"] = ui.column().classes("w-full gap-0")

            with seccion_formulario("Apariencia", "Tonos suaves para el documento."):
                for clave in ("color_principal", "color_barra_factura", "color_tabla"):
                    campo_edituable(
                        clave, _etiquetas()[clave], placeholder="#3A0088"
                    )

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
                    campo_edituable(clave, _etiquetas()[clave])

            if _recomendaciones_pendientes(cliente):
                with ui.element("section").classes("orq-seccion w-full"):
                    ui.label("Recomendaciones automáticas").classes("orq-seccion-titulo")
                    ui.label(
                        "Sugerencias disponibles cuando haya suficiente historial."
                    ).classes("orq-seccion-ayuda")
                    estado_vacio("Sin evaluar")

            barra_acciones("Guardar", reintentar_guardado, destino_cancelar="/")

    def cargar() -> None:
        nonlocal configuracion, vista_logo
        contenido.clear()
        mensajes.clear()
        errores_campos.clear()
        campos.clear()
        try:
            datos = obtener_configuracion(cliente)
        except ErrorApi as error:
            if error.status_code != 404:
                with contenido:
                    mostrar_error(contenido, error)
                    boton_orquidea("Reintentar", cargar, variante="secundario")
                return
            datos = {}
        except Exception as error:
            texto = MENSAJE_CONEXION if es_error_de_conexion(error) else MENSAJE_CARGA
            aviso_con_reintento(contenido, texto, cargar)
            return
        configuracion = datos if isinstance(datos, dict) else {}
        montar_formulario(not bool(configuracion))

    campos: dict[str, Any] = {}
    vista_logo: Any = None
    cargar()
