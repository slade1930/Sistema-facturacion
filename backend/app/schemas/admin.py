"""Listados y métricas globales para administración. Rol admin; etapa A."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.inventario import TipoMovimiento

DineroStock = Decimal  # NUMERIC(14,2), sin redondeo adicional en la API.


class InventarioRead(BaseModel):
    producto_id: int
    nombre_producto: str
    sku: str
    existencias: Decimal
    stock_minimo: Decimal
    actualizado_en: datetime | None = None


class InventarioActualizar(BaseModel):
    existencias: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    stock_minimo: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2
    )
    motivo: str | None = Field(default=None, max_length=200)


class MovimientoInventarioRead(BaseModel):
    id: int
    producto_id: int
    fecha: datetime
    tipo: TipoMovimiento
    cantidad: Decimal
    motivo: str
    factura_id: int | None = None
    cuenta_id: int | None = None
