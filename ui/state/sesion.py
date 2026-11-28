from dataclasses import dataclass, field
from typing import Any

from nicegui import app, ui


async def conectar_storage() -> None:
    """Habilita el almacenamiento de la pestaña antes de leer el carrito."""
    await ui.context.client.connected()


def contar_carrito(carrito: list[dict[str, Any]]) -> int:
    """Unidades del carrito, para el distintivo del encabezado."""
    total = 0
    for item in carrito:
        try:
            total += int(float(item.get("cantidad") or 0))
        except (TypeError, ValueError):
            continue
    return max(total, 0)


def actualizar_contador(carrito: list[dict[str, Any]]) -> None:
    """Refresca el distintivo y lo guarda para la próxima carga de página."""
    cantidad = contar_carrito(carrito)
    try:
        ui.run_javascript(
            "var n=" + str(cantidad) + ";"
            "try{sessionStorage.setItem('orq_carrito_count',String(n))}catch(e){};"
            "document.querySelectorAll('.orq-contador-carrito').forEach("
            "function(e){e.textContent=n>0?String(n):''});"
        )
    except Exception:
        pass


@dataclass
class Sesion:
    _carrito_local: list[dict[str, Any]] = field(default_factory=list, repr=False)
    ultima_factura: dict[str, Any] | None = None
    filtros_historial: dict[str, Any] = field(default_factory=dict)
    datos_cliente: dict[str, Any] = field(default_factory=dict)

    @property
    def carrito(self) -> list[dict[str, Any]]:
        """Carrito de la pestaña; fuera de una interfaz activa usa una lista local."""
        try:
            return app.storage.tab.setdefault("carrito", [])
        except Exception:
            return self._carrito_local

    @carrito.setter
    def carrito(self, valor: list[dict[str, Any]]) -> None:
        try:
            app.storage.tab["carrito"] = valor
        except Exception:
            self._carrito_local = valor


sesion = Sesion()
