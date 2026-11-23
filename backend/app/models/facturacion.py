from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ConfiguracionNegocio(TimestampMixin, Base):
    __tablename__ = "configuracion_negocio"
    __table_args__ = (
        CheckConstraint("tasa_itbms >= 0", name="ck_configuracion_negocio_tasa"),
    )

    id = Column(Integer, primary_key=True)
    razon_social = Column(String(200), nullable=False)
    ruc = Column(String(20), nullable=False, unique=True)
    direccion = Column(String(300))
    telefono = Column(String(30))
    email = Column(String(150))
    tasa_itbms = Column(
        Numeric(5, 2), nullable=False, default=Decimal("7.00"), server_default="7.00"
    )
    prefijo_factura = Column(String(4), nullable=False, default="FAC", server_default="FAC")
    prefijo_orden = Column(String(4), nullable=False, default="OC", server_default="OC")


class ContadorSerie(TimestampMixin, Base):
    __tablename__ = "contador_serie"
    __table_args__ = (
        UniqueConstraint("prefijo", "anio", name="uq_contador_serie_prefijo_anio"),
        CheckConstraint("anio BETWEEN 1900 AND 9999", name="ck_contador_serie_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_serie_ultimo"),
    )

    id = Column(Integer, primary_key=True)
    prefijo = Column(String(4), nullable=False)
    anio = Column(SmallInteger, nullable=False)
    ultimo_numero = Column(Integer, nullable=False, default=0, server_default="0")


class ContadorOrdenCompra(TimestampMixin, Base):
    __tablename__ = "contador_orden_compra"
    __table_args__ = (
        UniqueConstraint("prefijo", "anio", name="uq_contador_orden_compra_prefijo_anio"),
        CheckConstraint("anio BETWEEN 1900 AND 9999", name="ck_contador_orden_compra_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_orden_compra_ultimo"),
    )

    id = Column(Integer, primary_key=True)
    prefijo = Column(String(4), nullable=False, default="OC", server_default="OC")
    anio = Column(SmallInteger, nullable=False)
    ultimo_numero = Column(Integer, nullable=False, default=0, server_default="0")


class Factura(TimestampMixin, Base):
    __tablename__ = "factura"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('EMITIDA','ANULADA')",
            name="ck_factura_estado",
        ),
        CheckConstraint(
            "subtotal >= 0 AND itbms >= 0 AND total >= 0",
            name="ck_factura_totales",
        ),
        CheckConstraint(
            "estado <> 'ANULADA' OR "
            "(motivo_anulacion IS NOT NULL AND anulada_en IS NOT NULL)",
            name="ck_factura_anulacion",
        ),
        Index("ix_factura_fecha_emision", "fecha_emision"),
    )

    id = Column(Integer, primary_key=True)
    numero_factura = Column(String(20), nullable=False, unique=True)
    fecha_emision = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_vencimiento = Column(DateTime(timezone=True))

    negocio_razon_social = Column(String(200), nullable=False)
    negocio_ruc = Column(String(20), nullable=False)
    negocio_direccion = Column(String(300))

    cliente_nombre = Column(String(200), nullable=False)
    cliente_ruc = Column(String(20))
    cliente_direccion = Column(String(300))

    subtotal = Column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    itbms = Column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    total = Column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )

    codigo_verificacion = Column(String(32), nullable=False, unique=True)
    estado = Column(String(15), nullable=False, default="EMITIDA", server_default="EMITIDA")
    motivo_anulacion = Column(String(300))
    anulada_en = Column(DateTime(timezone=True))

    factura_generada_id = Column(
        Integer,
        comment=(
            "Referencia debil al pedido convertido o factura duplicada. "
            "Sin FK y sin UNIQUE."
        ),
    )

    lineas = relationship(
        "LineaFactura", back_populates="factura", cascade="all, delete-orphan"
    )


class LineaFactura(TimestampMixin, Base):
    __tablename__ = "linea_factura"
    __table_args__ = (
        UniqueConstraint(
            "factura_id", "numero_linea", name="uq_linea_factura_factura_numero"
        ),
        CheckConstraint(
            "(tasa_itbms IS NULL AND impuesto = 0) OR "
            "(tasa_itbms IS NOT NULL AND tasa_itbms >= 0)",
            name="ck_linea_factura_itbms",
        ),
        Index("ix_linea_factura_factura", "factura_id"),
    )

    id = Column(Integer, primary_key=True)
    factura_id = Column(
        Integer, ForeignKey("factura.id", ondelete="CASCADE"), nullable=False
    )
    numero_linea = Column(Integer, nullable=False)
    descripcion = Column(String(300), nullable=False)
    cantidad = Column(Numeric(12, 3), nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    tasa_itbms = Column(Numeric(5, 2))
    base_imponible = Column(Numeric(12, 2), nullable=False)
    impuesto = Column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    total_linea = Column(Numeric(12, 2), nullable=False)

    factura = relationship("Factura", back_populates="lineas")
