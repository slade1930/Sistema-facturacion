from typing import Any

from nicegui import ui

from components.admin.seguridad import exigir_admin
from components.forms import boton_enlace, boton_orquidea, mostrar_error
from components.layout import montar_layout
from components.shared import estado_vacio, sello_estado, total_animado
from state.cliente_api import ClienteApi, ErrorApi

cliente = ClienteApi()

LIMITE_MAXIMO = 500
PEDIDOS_POR_PAGINA = 20


def listar_pendientes(
    cliente_api: ClienteApi, limite: int = LIMITE_MAXIMO
) -> list[dict[str, Any]]:
    return cliente_api.get(
        "/api/v1/pedidos/por-facturar",
        params={"limite": limite},
    )


def _valor(datos: dict[str, Any], clave: str) -> str:
    valor = datos.get(clave)
    return "" if valor is None else str(valor)


def calcular_paginacion(
    total_pedidos: int,
    pagina: int,
    por_pagina: int = PEDIDOS_POR_PAGINA,
) -> tuple[int, int, int]:
    total_paginas = max(
        1,
        (total_pedidos + por_pagina - 1) // por_pagina,
    )

    pagina = max(1, min(pagina, total_paginas))

    inicio = (pagina - 1) * por_pagina
    fin = min(inicio + por_pagina, total_pedidos)

    return pagina, inicio, fin


@ui.page("/pedidos/por-facturar")
def pagina_pedidos_pendientes(limite: int = LIMITE_MAXIMO) -> None:
    if not exigir_admin():
        return
    montar_layout("Pedidos por facturar", ruta_activa="/pedidos/por-facturar")

    limite = min(max(limite, 1), LIMITE_MAXIMO)

    mensajes = ui.column()
    contenedor = ui.column().classes("w-full")
    paginacion = ui.row().classes("orq-paginacion w-full")
    with paginacion:
        resumen = ui.label().classes("orq-resumen")
        botones_pagina = ui.row().classes("orq-paginacion-grupo")

    pedidos_cargados: list[dict[str, Any]] = []
    pagina_actual = 1

    def renderizar() -> None:
        nonlocal pagina_actual

        contenedor.clear()
        botones_pagina.clear()

        total_pedidos = len(pedidos_cargados)
        pagina_actual, inicio, fin = calcular_paginacion(
            total_pedidos,
            pagina_actual,
        )
        total_paginas = max(
            1,
            (total_pedidos + PEDIDOS_POR_PAGINA - 1) // PEDIDOS_POR_PAGINA,
        )

        resumen.text = (
            f"Mostrando {inicio + 1}-{fin} de {total_pedidos} pedidos"
        )

        if not pedidos_cargados:
            with contenedor:
                estado_vacio(
                    "No hay pedidos pendientes de facturar.",
                    "Cuando armes un pedido, aparecerá acá.",
                )
            return

        for pedido in pedidos_cargados[inicio:fin]:
            pedido_id = _valor(pedido, "id")
            with contenedor:
                with ui.element("article").classes("orq-ticket w-full"):
                    with ui.row().classes("orq-ticket-cabecera w-full"):
                        with ui.column().classes("gap-0"):
                            ui.label(
                                f"Pedido #{pedido_id} · "
                                f"{_valor(pedido, 'estado')}"
                            ).classes("orq-ticket-folio")
                            ui.label("Listo para revisar").classes(
                                "orq-ticket-fecha"
                            )
                        sello_estado(_valor(pedido, "estado"))

                    with ui.row().classes("orq-ticket-datos w-full"):
                        with ui.element("div").classes("orq-dato"):
                            ui.label("Cliente").classes("orq-dato-etiqueta")
                            ui.label(_valor(pedido, "cliente_id")).classes(
                                "orq-dato-valor"
                            )
                        with ui.element("div").classes("orq-dato"):
                            ui.label("Líneas").classes("orq-dato-etiqueta")
                            ui.label(
                                str(len(pedido.get("lineas") or []))
                            ).classes("orq-dato-valor")
                        notas = _valor(pedido, "notas")
                        if notas:
                            with ui.element("div").classes("orq-dato"):
                                ui.label("Notas").classes("orq-dato-etiqueta")
                                ui.label(notas).classes("orq-dato-valor")

                    with ui.row().classes("w-full items-end justify-between"):
                        with ui.row().classes("orq-ticket-acciones"):
                            boton_enlace(
                                "Ver detalle",
                                f"/pedidos/detalle?pedido_id={pedido_id}",
                                variante="secundario",
                            )
                            boton_enlace(
                                "Facturar",
                                f"/pedidos/convertir-a-factura?pedido_id={pedido_id}",
                            )
                        with ui.column().classes("gap-0"):
                            total_animado(
                                _valor(pedido, "total_estimado"),
                                etiqueta="Total estimado",
                            )

        with botones_pagina:
            if pagina_actual > 1:
                boton_orquidea(
                    "Anterior",
                    lambda: cambiar_pagina(-1),
                    variante="secundario",
                )
            ui.label(f"Página {pagina_actual} de {total_paginas}").classes(
                "orq-resumen"
            )
            if pagina_actual < total_paginas:
                boton_orquidea(
                    "Siguiente",
                    lambda: cambiar_pagina(1),
                    variante="secundario",
                )

    def cambiar_pagina(cambio: int) -> None:
        nonlocal pagina_actual

        pagina_actual, _, _ = calcular_paginacion(
            len(pedidos_cargados),
            pagina_actual + cambio,
        )

        renderizar()

    def cargar() -> None:
        mensajes.clear()

        try:
            pedidos_cargados.extend(listar_pendientes(cliente, limite))
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return

        renderizar()

    cargar()
