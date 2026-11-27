
from typing import Any

from nicegui import ui

from components.layout import montar_layout
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
    montar_layout("Pedidos por facturar")

    limite = min(max(limite, 1), LIMITE_MAXIMO)

    mensajes = ui.column()
    contenedor = ui.column().classes("w-full")
    paginacion = ui.row().classes("w-full items-center justify-center gap-4")

    pedidos_cargados: list[dict[str, Any]] = []
    pagina_actual = 1

    def renderizar() -> None:
        nonlocal pagina_actual

        contenedor.clear()
        paginacion.clear()

        if not pedidos_cargados:
            with contenedor:
                ui.label(
                    "No hay pedidos pendientes de facturar."
                ).classes("text-grey")
            return

        total_pedidos = len(pedidos_cargados)

        pagina_actual, inicio, fin = calcular_paginacion(
            total_pedidos,
            pagina_actual,
        )

        total_paginas = max(
            1,
            (total_pedidos + PEDIDOS_POR_PAGINA - 1)
            // PEDIDOS_POR_PAGINA,
        )

        pedidos_pagina = pedidos_cargados[inicio:fin]

        for pedido in pedidos_pagina:
            with contenedor:
                with ui.card().classes("w-full"):
                    ui.label(
                        f"Pedido #{_valor(pedido, 'id')} · "
                        f"{_valor(pedido, 'estado')}"
                    ).classes("text-h6")

                    with ui.row().classes("w-full justify-between"):
                        ui.label("Cliente").classes("text-grey")
                        ui.label(_valor(pedido, "cliente_id"))

                    with ui.row().classes("w-full justify-between"):
                        ui.label("Total estimado").classes("text-grey")
                        ui.label(_valor(pedido, "total_estimado"))

                    with ui.row().classes("w-full justify-between"):
                        ui.label("Líneas").classes("text-grey")
                        ui.label(str(len(pedido.get("lineas", []))))

                    notas = _valor(pedido, "notas")
                    if notas:
                        ui.label(f"Notas: {notas}").classes("text-caption")

                    with ui.row().classes("gap-2 mt-2"):
                        ui.button(
                            "Ver detalle",
                            on_click=lambda p=pedido: ui.navigate.to(
                                f"/pedidos/detalle?id={p['id']}"
                            ),
                        )
                        ui.button(
                            "Facturar",
                            on_click=lambda p=pedido: ui.navigate.to(
                                f"/pedidos/convertir-a-factura?id={p['id']}"
                            ),
                        )

        if total_paginas > 1:
            with paginacion:
                if pagina_actual > 1:
                    ui.button(
                        "Anterior",
                        on_click=lambda: cambiar_pagina(-1),
                    )

                ui.label(
                    f"Página {pagina_actual} de {total_paginas}"
                )

                if pagina_actual < total_paginas:
                    ui.button(
                        "Siguiente",
                        on_click=lambda: cambiar_pagina(1),
                    )

                ui.label(
                    f"Mostrando {inicio + 1}-{fin} "
                    f"de {total_pedidos} pedidos"
                ).classes("text-grey")

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
            pedidos_cargados.extend(
                listar_pendientes(cliente, limite)
            )
        except ErrorApi as error:
            with mensajes:
                ui.label(
                    f"{error.code}: {error.detail}"
                ).classes("text-negative")
            return

        renderizar()

    cargar()
