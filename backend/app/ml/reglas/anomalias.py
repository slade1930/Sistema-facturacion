"""Reglas base de anomalías: sin modelo entrenado, solo reglas simples.

Cada regla recibe los rasgos de UNA factura (y el historial si lo necesita) y
devuelve un Hallazgo si salta, o None si no. Trabajan con datos en memoria.
El ML sugiere: nada de esto bloquea ni anula una factura.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.ml.features.anomalias import RasgosFactura

# Umbrales de las reglas base. Se cambian aquí, en un solo lugar.
PERCENTIL_MONTO = 95
MIN_HISTORIAL_MONTO = 20  # con menos facturas, el percentil no es confiable


@dataclass(frozen=True)
class Hallazgo:
    regla: str
    motivo: str
    peso: int  # cuántos puntos (de 100) suma esta regla


def percentil(valores, p):
    """Percentil p (0-100) por interpolación lineal. Sin librerías externas."""
    if not valores:
        raise ValueError("No hay valores para calcular el percentil.")
    ordenados = sorted(valores)
    posicion = (len(ordenados) - 1) * Decimal(p) / Decimal(100)
    abajo = int(posicion)
    arriba = min(abajo + 1, len(ordenados) - 1)
    fraccion = posicion - abajo
    return ordenados[abajo] + (ordenados[arriba] - ordenados[abajo]) * fraccion


def regla_monto_alto(factura: RasgosFactura, historial: list[RasgosFactura]):
    """Salta si el total supera el percentil alto del historial."""
    if len(historial) < MIN_HISTORIAL_MONTO:
        return None  # sin evaluar: no hay historial suficiente
    limite = percentil([f.total for f in historial], PERCENTIL_MONTO)
    if factura.total > limite:
        return Hallazgo(
            regla="monto_alto",
            motivo=f"Total {factura.total} supera el percentil {PERCENTIL_MONTO} ({limite:.2f}).",
            peso=40,
        )
    return None