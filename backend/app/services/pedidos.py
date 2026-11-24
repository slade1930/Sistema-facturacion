"""Cálculos de pedidos B2B: precios por presentación y subtotales."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

CENTAVOS = Decimal("0.01")


class Presentacion(str, Enum):
    CAJA = "caja"
    MEDIA_CAJA = "media_caja"
    UNIDAD = "unidad"


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def precio_unitario(
    precios: dict[Presentacion, Decimal], presentacion: Presentacion
) -> Decimal:
    if presentacion not in precios:
        raise ValueError(f"No hay precio para {presentacion.value}")
    return precios[presentacion]


def subtotal_linea(precio: Decimal, cantidad: int) -> Decimal:
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")
    return redondear(precio * cantidad)


def subtotal_pedido(subtotales_lineas: list[Decimal]) -> Decimal:
    return redondear(sum(subtotales_lineas, Decimal("0")))


@dataclass(frozen=True)
class LineaPedido:
    descripcion: str
    presentacion: Presentacion
    cantidad: int
    precio: Decimal

    def __post_init__(self):
        if not isinstance(self.precio, Decimal):
            raise TypeError("El precio debe ser Decimal")
        if self.precio < 0:
            raise ValueError("El precio no puede ser negativo")
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")

    @property
    def subtotal(self) -> Decimal:
        return subtotal_linea(self.precio, self.cantidad)


@dataclass(frozen=True)
class ResumenPedido:
    subtotales_lineas: list[Decimal]
    subtotal: Decimal


def calcular_pedido(lineas: list[LineaPedido]) -> ResumenPedido:
    if not lineas:
        raise ValueError("El pedido no tiene líneas")
    subtotales = [l.subtotal for l in lineas]
    return ResumenPedido(subtotales, subtotal_pedido(subtotales))


@dataclass(frozen=True)
class LineaFacturaBorrador:
    """Línea lista para pasarle al servicio de facturación (equipo 2)."""
    descripcion: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


def pedido_a_lineas_factura(lineas: list[LineaPedido]) -> list[LineaFacturaBorrador]:
    if not lineas:
        raise ValueError("El pedido no tiene líneas")
    return [
        LineaFacturaBorrador(
            descripcion=f"{l.descripcion} ({l.presentacion.value})",
            cantidad=l.cantidad,
            precio_unitario=l.precio,
            subtotal=l.subtotal,
        )
        for l in lineas
    ]


# TODO (coordinar con equipo 2, facturacion):
#  - qué líneas llevan ITBMS (campo "gravado"): lo define el producto de Elian
#  - número FAC-AAAA-0001, totales y descuentos: vienen de serie.py y totales.py
#  - guardar la factura: requiere los modelos de postgres