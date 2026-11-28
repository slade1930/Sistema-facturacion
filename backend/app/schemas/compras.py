"""Líneas, idempotencia y respuesta de la compra con factura. Rol empresa; etapa A."""

from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.catalogo import TipoEmpaque


class LineaCompra(BaseModel):
    producto_id: int = Field(gt=0)
    tipo_empaque: TipoEmpaque = TipoEmpaque.CAJA
    cantidad: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class CompraCreate(BaseModel):
    lineas: list[LineaCompra] = Field(min_length=1)
    clave_idempotencia: str | None = Field(default=None, max_length=64)
    notas: str | None = Field(default=None, max_length=500)


class CompraResponse(BaseModel):
    pedido_id: int
    factura_id: int
    numero_serie: str
    total: Decimal
    pdf_url: str
    reutilizada: bool = False
