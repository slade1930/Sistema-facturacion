"""Rasgos de una factura para detectar anomalías.

Trabaja con datos en memoria: no lee la base ni archivos. Así las reglas
se pueden probar sin Docker y sin los CSV de ejemplo.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class RasgosFactura:
    factura_id: int
    cliente: str                 # RUC si lo tiene, si no el nombre
    fecha: date
    total: Decimal
    descuento_max_pct: Decimal   # el descuento más alto entre sus líneas
    anulada: bool


def rasgos_de_factura(factura) -> RasgosFactura:
    """Convierte una Factura (con sus líneas) en RasgosFactura."""
    estado = getattr(factura.estado, "value", factura.estado)
    return RasgosFactura(
        factura_id=factura.id,
        cliente=factura.cliente_ruc or factura.cliente_nombre,
        fecha=factura.fecha,
        total=factura.total,
        descuento_max_pct=max(
            (linea.descuento_pct for linea in factura.lineas),
            default=Decimal("0"),
        ),
        anulada=(estado == "anulada"),
    )


def rasgos_de_facturas(facturas) -> list[RasgosFactura]:
    return [rasgos_de_factura(f) for f in facturas]
