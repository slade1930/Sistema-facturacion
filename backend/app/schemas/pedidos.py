"""Esquemas Pydantic v2 para pedidos B2B y sus líneas."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.catalogo import EstadoPedido, TipoEmpaque

DineroPedido = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
CantidadPedido = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class LineaPedidoB2BCreate(BaseModel):
    producto_id: int = Field(gt=0)
    tipo_empaque: TipoEmpaque = TipoEmpaque.CAJA
    cantidad: CantidadPedido
    subtotal: DineroPedido
    orden: int = Field(default=1, ge=0)


class LineaPedidoB2BUpdate(BaseModel):
    producto_id: int | None = Field(default=None, gt=0)
    tipo_empaque: TipoEmpaque | None = None
    cantidad: CantidadPedido | None = None
    subtotal: DineroPedido | None = None
    orden: int | None = Field(default=None, ge=0)


class LineaPedidoB2BRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pedido_id: int
    producto_id: int
    tipo_empaque: TipoEmpaque
    cantidad: CantidadPedido
    subtotal: DineroPedido
    orden: int


class PedidoB2BCreate(BaseModel):
    cliente_id: int = Field(gt=0)
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    total_estimado: DineroPedido = Decimal("0.00")
    notas: str | None = None
    lineas: list[LineaPedidoB2BCreate] = Field(default_factory=list)


class PedidoB2BUpdate(BaseModel):
    estado: EstadoPedido | None = None
    total_estimado: DineroPedido | None = None
    notas: str | None = None
    factura_generada_id: int | None = Field(default=None, gt=0)


class PedidoB2BRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    estado: EstadoPedido
    total_estimado: DineroPedido
    notas: str | None
    factura_generada_id: int | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    lineas: list[LineaPedidoB2BRead] = Field(default_factory=list)
