"""Esquemas para el cálculo del carrito B2B.

El carrito no se persiste: solo recibe líneas y devuelve precios,
subtotales y totales estimados calculados con los servicios existentes.
"""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.catalogo import TipoEmpaque
from app.schemas.pedidos import CantidadPedido, DineroPedido


class CarritoLineaInput(BaseModel):
    producto_id: int = Field(gt=0)
    tipo_empaque: TipoEmpaque = TipoEmpaque.CAJA
    cantidad: CantidadPedido


class CarritoCalcularRequest(BaseModel):
    lineas: list[CarritoLineaInput] = Field(min_length=1)


class CarritoLineaCalculo(BaseModel):
    producto_id: int
    descripcion: str
    tipo_empaque: TipoEmpaque
    cantidad: CantidadPedido
    precio_unitario: DineroPedido
    subtotal: DineroPedido


class CarritoCalcularResponse(BaseModel):
    lineas: list[CarritoLineaCalculo]
    subtotal: Decimal
    descuento_total: Decimal
    base_gravada: Decimal
    base_exenta: Decimal
    itbms: Decimal
    total: Decimal
