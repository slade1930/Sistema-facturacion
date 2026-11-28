from typing import Any

from nicegui import ui

from components.forms import (
    boton_orquidea,
    campo_orquidea,
    mostrar_error,
    selector_orquidea,
)
from components.layout import montar_layout
from components.shared import estado_cargando, estado_vacio, tabla_orquidea
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
    {{
      props.value === 'emitida' ? 'Emitida' :
      (props.value === 'anulada' ? 'Anulada' : 'En revisión')
    }}
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
    montar_layout("Facturas emitidas", ruta_activa="/facturacion/historial")

    guardado = sesion.filtros_historial
    with ui.row().classes("orq-filtros w-full items-end") as filtros_fila:
        cliente_input = campo_orquidea(
            "Cliente", value=guardado.get("cliente", "")
        ).classes("w-40")
        estado_input = selector_orquidea(
            "Estado",
            {
                "": "Todos",
                "emitida": "Emitida",
                "anulada": "Anulada",
                "en_revision": "En revisión",
            },
            buscar=False,
            value=guardado.get("estado") or "",
        ).classes("w-32")
        fecha_desde = ui.date_input(
            "Desde", value=guardado.get("fecha_desde") or ""
        ).props("stack-label").classes("orq-campo w-32")
        fecha_hasta = ui.date_input(
            "Hasta", value=guardado.get("fecha_hasta") or ""
        ).props("stack-label").classes("orq-campo w-32")
        por_pagina = selector_orquidea(
            "Por página",
            [10, 20, 50],
            buscar=False,
            value=guardado.get("limite", 20),
        ).classes("w-28")

    mensajes = ui.column()
    cargando = ui.column().classes("w-full")
    resultado = ui.column().classes("w-full")

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

    def pintar(items: list[dict[str, Any]]) -> None:
        resultado.clear()
        with resultado:
            if not items:
                estado_vacio(
                    "Aún no hay facturas con estos filtros.",
                    "Prueba con otros criterios o emite la primera.",
                )
                return
            tablero = tabla_orquidea(list(COLUMNAS), items, row_key="id")
            tablero.add_slot("body-cell-estado", SELLO_FILA)

    def cargar() -> None:
        nonlocal desplazamiento
        filtros = leer_filtros()
        mensajes.clear()
        resultado.clear()
        cargando.clear()
        with cargando:
            estado_cargando(5)

        try:
            datos = consultar(cliente, filtros)
        except ErrorApi as error:
            cargando.clear()
            mostrar_error(mensajes, error)
            return

        cargando.clear()
        sesion.filtros_historial = dict(filtros)
        filas_actuales = filas(datos.get("items", []))
        pintar(filas_actuales)

        total = datos.get("total", 0)
        desplazamiento = datos.get("desplazamiento", desplazamiento)
        limite_actual = datos.get("limite", filtros["limite"])
        hasta_numero = min(desplazamiento + len(filas_actuales), total)
        inicio = desplazamiento + 1 if filas_actuales else 0
        resumen.text = f"Mostrando {inicio}-{hasta_numero} de {total}"

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

    def limpiar() -> None:
        nonlocal desplazamiento
        cliente_input.value = ""
        estado_input.value = ""
        fecha_desde.value = ""
        fecha_hasta.value = ""
        por_pagina.value = 20
        desplazamiento = 0
        cargar()

    with filtros_fila:
        with ui.row().classes("gap-2"):
            boton_orquidea("Buscar", buscar)
            boton_orquidea("Limpiar", limpiar, variante="texto")

    with ui.row().classes("orq-paginacion w-full"):
        resumen = ui.label().classes("orq-resumen")
        with ui.row().classes("orq-paginacion-grupo"):
            boton_orquidea("Anterior", anterior, variante="secundario")
            boton_orquidea("Siguiente", siguiente, variante="secundario")

    cargar()
