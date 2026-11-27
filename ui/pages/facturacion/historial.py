from typing import Any

from nicegui import ui

from components.forms import boton_orquidea, campo_orquidea, esqueleto, mensaje_error
from components.layout import montar_layout
from components.shared import estado_vacio
from components.tables import tabla_orquidea
from state.cliente_api import ClienteApi, ErrorApi
from state.sesion import sesion

cliente = ClienteApi()

COLUMNAS = (
    {"name": "numero_serie", "label": "Número", "field": "numero_serie", "align": "left"},
    {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "left"},
    {"name": "cliente_nombre", "label": "Cliente", "field": "cliente_nombre", "align": "left"},
    {"name": "condicion_pago", "label": "Condición", "field": "condicion_pago", "align": "left"},
    {"name": "total", "label": "Total", "field": "total", "align": "right"},
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
)

CAMPOS = (
    "id",
    "numero_serie",
    "fecha",
    "cliente_nombre",
    "condicion_pago",
    "total",
    "estado",
)

SELLO_FILA = """
<q-td :props="props">
  <span class="orq-sello"
        :class="props.value === 'emitida' ? 'orq-sello--emitida' :
                (props.value === 'anulada' ? 'orq-sello--anulada' : 'orq-sello--revision')">
    {{ props.value === 'en_revision' ? 'En revisión' : props.value }}
  </span>
</q-td>
"""


def consultar(cliente_api: ClienteApi, filtros: dict[str, Any]) -> dict[str, Any]:
    params = {
        "cliente": filtros.get("cliente") or None,
        "estado": filtros.get("estado") or None,
        "fecha_desde": filtros.get("fecha_desde") or None,
        "fecha_hasta": filtros.get("fecha_hasta") or None,
        "limite": filtros.get("limite", 20),
        "desplazamiento": filtros.get("desplazamiento", 0),
    }
    params = {clave: valor for clave, valor in params.items() if valor not in (None, "")}
    return cliente_api.get("/api/v1/historial", params=params)


def filas(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{campo: item.get(campo) for campo in CAMPOS} for item in items]


@ui.page("/facturacion/historial")
def pagina_historial() -> None:
    montar_layout("Historial de facturas", ruta_activa="/facturacion/historial")

    guardado = sesion.filtros_historial
    with ui.row().classes("orq-filtros w-full items-end"):
        cliente_input = campo_orquidea(
            "Cliente", value=guardado.get("cliente", "")
        ).classes("w-full")
        estado_input = ui.select(
            {
                "": "Todos",
                "emitida": "Emitida",
                "anulada": "Anulada",
                "en_revision": "En revisión",
            },
            label="Estado",
            value=guardado.get("estado") or "",
        ).classes("orq-campo")
        fecha_desde = ui.date(
            value=guardado.get("fecha_desde"), mask="YYYY-MM-DD"
        ).classes("orq-campo")
        fecha_hasta = ui.date(
            value=guardado.get("fecha_hasta"), mask="YYYY-MM-DD"
        ).classes("orq-campo")
        por_pagina = ui.select(
            [10, 20, 50],
            label="Por página",
            value=guardado.get("limite", 20),
        ).classes("orq-campo")

    resumen = ui.label().classes("orq-resumen")
    mensajes = ui.column()
    cargando = ui.column().classes("w-full gap-2")
    contenido = ui.column().classes("w-full")

    tablero = tabla_orquidea(list(COLUMNAS), [], row_key="id")
    tablero.add_slot("body-cell-estado", SELLO_FILA)

    desplazamiento = guardado.get("desplazamiento", 0)

    def leer_filtros() -> dict[str, Any]:
        return {
            "cliente": (cliente_input.value or "").strip(),
            "estado": estado_input.value or "",
            "fecha_desde": fecha_desde.value or "",
            "fecha_hasta": fecha_hasta.value or "",
            "limite": int(por_pagina.value or 20),
            "desplazamiento": desplazamiento,
        }

    def cargar() -> None:
        nonlocal desplazamiento
        filtros = leer_filtros()
        mensajes.clear()
        contenido.clear()
        cargando.clear()
        with cargando:
            for ancho in ("90%", "70%", "80%", "60%", "75%", "65%"):
                esqueleto(20, ancho)

        try:
            datos = consultar(cliente, filtros)
        except ErrorApi as error:
            cargando.clear()
            with mensajes:
                mensaje_error(f"{error.code}: {error.detail}")
                for item in error.errors:
                    mensaje_error(str(item))
            return

        sesion.filtros_historial = dict(filtros)
        filas_actuales = filas(datos.get("items", []))
        tablero.rows = filas_actuales
        tablero.update()
        cargando.clear()

        total = datos.get("total", 0)
        desplazamiento = datos.get("desplazamiento", desplazamiento)
        limite_actual = datos.get("limite", filtros["limite"])
        hasta_numero = min(desplazamiento + len(filas_actuales), total)
        inicio = desplazamiento + 1 if filas_actuales else 0
        resumen.text = (
            f"Mostrando {inicio}-{hasta_numero} de {total} "
            f"(límite {limite_actual})"
        )
        if not filas_actuales:
            with contenido:
                estado_vacio("Aún no hay facturas. Emite la primera.")

    def buscar() -> None:
        nonlocal desplazamiento
        desplazamiento = 0
        cargar()

    def anterior() -> None:
        nonlocal desplazamiento
        desplazamiento = max(0, desplazamiento - int(por_pagina.value or 20))
        cargar()

    def siguiente() -> None:
        nonlocal desplazamiento
        desplazamiento += int(por_pagina.value or 20)
        cargar()

    with ui.row().classes("orq-acciones gap-2"):
        boton_orquidea("Buscar", buscar)
        boton_orquidea("Anterior", anterior, variante="secundario")
        boton_orquidea("Siguiente", siguiente, variante="secundario")

    cargar()
