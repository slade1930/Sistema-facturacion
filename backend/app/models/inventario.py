"""Inventario y movimientos por producto. Admin y compras; etapa A."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

BIGINT = BigInteger().with_variant(Integer, "sqlite")


def _valores(enum_cls):
    return [miembro.value for miembro in enum_cls]


class TipoMovimiento(str, Enum):
    ENTRADA = "entrada"
    SALIDA = "salida"
    AJUSTE = "ajuste"


class Inventario(Base):
    __tablename__ = "inventario"
    __table_args__ = (
        CheckConstraint("existencias >= 0", name="ck_inventario_existencias"),
        CheckConstraint("stock_minimo >= 0", name="ck_inventario_minimo"),
    )

    producto_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("producto.id", ondelete="CASCADE"), primary_key=True
    )
    existencias: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    stock_minimo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_movimiento_inventario_cantidad"),
        Index("ix_movimiento_inventario_producto", "producto_id"),
        Index("ix_movimiento_inventario_factura", "factura_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("producto.id", ondelete="RESTRICT"), nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    tipo: Mapped[TipoMovimiento] = mapped_column(
        SAEnum(
            TipoMovimiento,
            name="tipo_movimiento_inventario",
            values_callable=_valores,
        ),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    motivo: Mapped[str] = mapped_column(String(200), nullable=False)
    factura_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("factura.id", ondelete="SET NULL"), nullable=True
    )
    cuenta_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("cuenta.id", ondelete="SET NULL"), nullable=True
    )
