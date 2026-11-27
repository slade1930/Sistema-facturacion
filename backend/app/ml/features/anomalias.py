"""Rasgos de una factura para detectar anomalías.

Trabaja con datos en memoria: no lee la base ni archivos. Así las reglas
se pueden probar sin Docker y sin los CSV de ejemplo.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
import unicodedata


@dataclass(frozen=True)
class RasgosFactura:
    factura_id: int
    cliente: str                 # RUC si lo tiene, si no el nombre
    fecha: date
    total: Decimal
    descuento_max_pct: Decimal   # el descuento más alto entre sus líneas
    anulada: bool


def normalizar_cliente(valor: str) -> str:
    """Clave estable para comparar clientes (RUC o razón social).

    Quita acentos, puntuación y espacios sobrantes, y deja solo lo que
    identifica al cliente. Así "Acme S.A." y "acme s.a." son el mismo.
    """
    sin_acentos = unicodedata.normalize("NFKD", str(valor or ""))
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", sin_acentos.lower())


def clientes_coinciden(uno: str, otro: str) -> bool:
    """Dos clientes son el mismo si coinciden por RUC o por nombre base.

    El sufijo legal (S.A., SRL, Ltda.) no distingue clientes: "Acme" y
    "Acme S.A." apuntan al mismo. Sí importa el resto ("Acme Sur" no es
    "Acme").
    """
    a, b = normalizar_cliente(uno), normalizar_cliente(otro)
    if not a or not b:
        return False
    if a == b:
        return True
    sufijos = ("sa", "srl", "ltda", "sc", "sac")
    base_a = next((a[: -len(s)] for s in sufijos if a.endswith(s) and len(a) > len(s)), a)
    base_b = next((b[: -len(s)] for s in sufijos if b.endswith(s) and len(b) > len(s)), b)
    return base_a == base_b


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
