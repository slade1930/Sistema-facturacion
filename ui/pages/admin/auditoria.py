"""Auditoría global del administrador; etapa C2."""

from typing import Any

from nicegui import ui

from components.admin import (
    cliente_admin,
    conectar_sesion,
    exigir_admin,
    montar_admin,
    tabla_admin,
    texto,
)
from components.forms import boton_orquidea, campo_orquidea, mostrar_error
from components.shared import estado_cargando
from state.cliente_api import ErrorApi

LIMITE = 20

COLUMNAS = (
    {"name": "id", "label": "Registro", "field": "id", "align": "left"},
    {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "left", "fecha": True},
    {"name": "accion", "label": "Acción", "field": "accion", "align": "left"},
    {"name": "cuenta", "label": "Cuenta", "field": "cuenta_id", "align": "left"},
    {"name": "detalle", "label": "Detalle", "field": "detalle", "align": "left"},
    {"name": "ip", "label": "Dirección", "field": "ip", "align": "left"},
)


def listar_auditoria(api: Any, filtros: dict[str, Any]) -> dict[str, Any]:
    return api.get("/api/v1/admin/auditoria", params=filtros)


@ui.page("/admin/auditoria")
async def pagina_auditoria_admin() -> None:
    await conectar_sesion()
    if not exigir_admin():
        return
    montar_admin("Auditoría", ruta_activa="/admin/auditoria")

    mensajes = ui.column().classes("w-full")
    desplazamiento = {"valor": 0}
    with ui.row().classes("w-full items-end gap-3"):
        accion = campo_orquidea("Acción")
        cuenta = campo_orquidea("ID de cuenta")
        desde = campo_orquidea("Desde", placeholder="AAAA-MM-DD")
        hasta = campo_orquidea("Hasta", placeholder="AAAA-MM-DD")
        boton_orquidea("Buscar", lambda: _buscar())

    tabla_zone = ui.column().classes("w-full")
    paginacion = ui.row().classes("orq-paginacion w-full")
    with paginacion:
        resumen = ui.label().classes("orq-resumen")
        boton_anterior = boton_orquidea("Anterior", lambda: _mover(-LIMITE), variante="texto")
        boton_siguiente = boton_orquidea("Siguiente", lambda: _mover(LIMITE), variante="texto")
    with tabla_zone:
        estado_cargando(3)

    def _filtros() -> dict[str, Any]:
        filtros: dict[str, Any] = {
            "desplazamiento": desplazamiento["valor"],
            "limite": LIMITE,
        }
        for campo, clave in (
            (accion, "accion"),
            (cuenta, "cuenta_id"),
            (desde, "desde"),
            (hasta, "hasta"),
        ):
            valor = str(campo.value or "").strip()
            if valor:
                filtros[clave] = valor
        return filtros

    def cargar() -> None:
        mensajes.clear()
        try:
            respuesta = listar_auditoria(cliente_admin(), _filtros())
        except ErrorApi as error:
            mostrar_error(mensajes, error)
            return
        except Exception:
            ui.label("No pudimos cargar la auditoría. Inténtalo de nuevo.").classes(
                "orq-error"
            )
            return
        items = list(respuesta.get("items") or [])
        total = int(respuesta.get("total") or 0)
        inicio = int(respuesta.get("desplazamiento") or 0)
        fin = min(inicio + len(items), total)
        resumen.text = (
            f"Mostrando {inicio + 1}-{fin} de {total}" if items else "Sin resultados"
        )
        boton_anterior.set_visibility(inicio > 0)
        boton_siguiente.set_visibility(fin < total)
        filas = []
        for evento in items:
            fila = dict(evento)
            fila["detalle"] = texto(evento.get("detalle"))
            fila["ip"] = texto(evento.get("ip"))
            filas.append(fila)
        tabla_zone.clear()
        with tabla_zone:
            tabla_admin(
                list(COLUMNAS),
                filas,
                mensaje_vacio="No hay eventos con estos filtros.",
            )

    def _buscar() -> None:
        desplazamiento["valor"] = 0
        cargar()

    def _mover(delta: int) -> None:
        desplazamiento["valor"] = max(0, desplazamiento["valor"] + delta)
        cargar()

    cargar()


__all__ = ["listar_auditoria", "pagina_auditoria_admin"]
