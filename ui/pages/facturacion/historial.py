from typing import Any

from nicegui import ui

from components.layout import montar_layout
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
    montar_layout("Historial de facturas")

    guardado = sesion.filtros_historial
    cliente_input = ui.input("Cliente", value=guardado.get("cliente", "")).classes("w-full")
    estado_input = ui.select(
        {
            "": "Todos",
            "emitida": "Emitida",
            "anulada": "Anulada",
            "en_revision": "En revisión",
        },
        label="Estado",
        value=guardado.get("estado") or "",
    )
    fecha_desde = ui.date(value=guardado.get("fecha_desde"), mask="YYYY-MM-DD")
    fecha_hasta = ui.date(value=guardado.get("fecha_hasta"), mask="YYYY-MM-DD")
    por_pagina = ui.select(
        [10, 20, 50],
        label="Por página",
        value=guardado.get("limite", 20),
    )

    resumen = ui.label().classes("text-grey")
    mensajes = ui.column()
    tablero = ui.table(columns=list(COLUMNAS), rows=[], row_key="id")

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

        try:
            datos = consultar(cliente, filtros)
        except ErrorApi as error:
            with mensajes:
                ui.label(f"{error.code}: {error.detail}").classes("text-negative")
                for item in error.errors:
                    ui.label(str(item)).classes("text-caption text-negative")
            return

        sesion.filtros_historial = dict(filtros)
        filas_actuales = filas(datos.get("items", []))
        tablero.rows = filas_actuales
        tablero.update()

        total = datos.get("total", 0)
        desplazamiento = datos.get("desplazamiento", desplazamiento)
        limite_actual = datos.get("limite", filtros["limite"])
        hasta_numero = min(desplazamiento + len(filas_actuales), total)
        inicio = desplazamiento + 1 if filas_actuales else 0
        resumen.text = (
            f"Mostrando {inicio}-{hasta_numero} de {total} "
            f"(límite {limite_actual})"
        )

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

    with ui.row().classes("gap-2 my-2"):
        ui.button("Buscar", on_click=buscar)
        ui.button("Anterior", on_click=anterior)
        ui.button("Siguiente", on_click=siguiente)

    cargar()
