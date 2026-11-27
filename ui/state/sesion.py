from dataclasses import dataclass, field
from typing import Any


@dataclass
class Sesion:
    carrito: list[dict[str, Any]] = field(default_factory=list)
    ultima_factura: dict[str, Any] | None = None
    filtros_historial: dict[str, Any] = field(default_factory=dict)
    datos_cliente: dict[str, Any] = field(default_factory=dict)


sesion = Sesion()
