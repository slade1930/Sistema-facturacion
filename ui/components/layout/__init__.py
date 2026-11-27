from nicegui import ui

from state.sesion import sesion

ENLACES = (
    ("Inicio", "/", "Inicio"),
    ("Nueva factura", "/facturacion/nueva", "Nueva"),
    ("Historial", "/facturacion/historial", "Historial"),
    ("Catálogo", "/catalogo", "Catálogo"),
    ("Pedidos", "/pedidos/por-facturar", "Pedidos"),
    ("Configuración", "/configuracion", "Config"),
    ("Verificar", "/verificar", "Verificar"),
)

MARCA = """
<svg viewBox="0 0 48 48" role="img" aria-label="Flor del Espíritu Santo">
  <path d="M24 42C24 31 14 27 10 19 6 11 13 5 24 13 35 5 42 11 38 19 34 27 24 31 24 42Z"
        fill="none" stroke="#F1EAFD" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M24 42V20m0 8-9-6m9 6 9-6" fill="none" stroke="#D4157F" stroke-width="2" stroke-linecap="round"/>
</svg>
"""


def montar_layout(
    titulo: str = "Sistema de facturación", *, ruta_activa: str | None = None
) -> None:
    activo = ruta_activa or next(
        (ruta for texto, ruta, _ in ENLACES if texto == titulo), "/"
    )
    migas = "Inicio" if titulo == "Sistema de facturación" else f"Inicio / {titulo}"

    with ui.drawer(side="left", fixed=False, value=True).classes("orq-rail"):
        with ui.column().classes("orq-marca w-full items-center"):
            ui.html(MARCA).classes("orq-petala")
            ui.label("Orquídea").classes("orq-nombre-marca")
        for texto, ruta, corto in ENLACES:
            clases = "orq-enlace"
            if ruta == activo:
                clases += " orq-activo"
            with ui.link(texto, ruta).classes(clases):
                ui.label(corto).classes("orq-enlace-texto-corto")
                ui.label(texto).classes("orq-enlace-texto-completo")
        ui.label("Sistema de facturación").classes("orq-pie-rail")

    with ui.column().classes("orq-contenido w-full"):
        with ui.row().classes("orq-cabecera w-full items-end justify-between"):
            with ui.column().classes("gap-0"):
                ui.label(migas).classes("orq-migas")
                ui.label(titulo).classes("orq-titulo")
                ultima = sesion.ultima_factura
                if ultima and ultima.get("numero_serie"):
                    ui.label(f"Último folio {ultima['numero_serie']}").classes(
                        "orq-resumen"
                    )
