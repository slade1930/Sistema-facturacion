from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

BIGINT = BigInteger().with_variant(Integer, "sqlite")


class ConfiguracionNegocio(Base):
    __tablename__ = "configuracion_negocio"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    empresa_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    empresa_ruc: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    mostrar_ruc: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    empresa_direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    empresa_correo: Mapped[str | None] = mapped_column(String(254), nullable=True)
    empresa_telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color_principal: Mapped[str | None] = mapped_column(String(7), nullable=True)
    color_barra_factura: Mapped[str | None] = mapped_column(String(7), nullable=True)
    color_tabla: Mapped[str | None] = mapped_column(String(7), nullable=True)
    datos_bancarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas_predeterminadas: Mapped[str | None] = mapped_column(Text, nullable=True)
    actualizado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ContadorSerie(Base):
    __tablename__ = "contador_serie"
    __table_args__ = (
        UniqueConstraint("anio", name="uq_contador_serie_anio"),
        CheckConstraint("anio BETWEEN 1900 AND 9999", name="ck_contador_serie_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_serie_ultimo"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class ContadorOrdenCompra(Base):
    __tablename__ = "contador_orden_compra"
    __table_args__ = (
        UniqueConstraint("anio", name="uq_contador_orden_compra_anio"),
        CheckConstraint("anio BETWEEN 1900 AND 9999", name="ck_contador_orden_compra_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_orden_compra_ultimo"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class Factura(Base):
    __tablename__ = "factura"
    __table_args__ = (
        CheckConstraint("estado IN ('EMITIDA','ANULADA')", name="ck_factura_estado"),
        CheckConstraint(
            "estado <> 'ANULADA' OR fecha_anulacion IS NOT NULL",
            name="ck_factura_anulacion",
        ),
        CheckConstraint(
            "subtotal >= 0 AND descuento_total >= 0 AND base_gravada >= 0 "
            "AND base_exenta >= 0 AND portes >= 0 AND itbms >= 0 AND total >= 0",
            name="ck_factura_totales",
        ),
        Index("ix_factura_fecha", "fecha"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    numero_serie: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    codigo_verificacion: Mapped[str] = mapped_column(
        String(12), nullable=False, unique=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    cliente_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cliente_ruc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mostrar_ruc: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    cliente_direccion: Mapped[str | None] = mapped_column(String(250), nullable=True)
    cliente_telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cliente_correo: Mapped[str | None] = mapped_column(String(254), nullable=True)
    sucursal: Mapped[str | None] = mapped_column(String(150), nullable=True)
    vendedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    orden_compra: Mapped[str | None] = mapped_column(String(60), nullable=True)
    condicion_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)
    portes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    descuento_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    base_gravada: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    base_exenta: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    itbms: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )

    estado: Mapped[str] = mapped_column(
        String(15), nullable=False, default="EMITIDA", server_default="EMITIDA"
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_anulacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    lineas: Mapped[list["LineaFactura"]] = relationship(
        "LineaFactura", back_populates="factura", cascade="all, delete-orphan"
    )


class LineaFactura(Base):
    __tablename__ = "linea_factura"
    __table_args__ = (
        UniqueConstraint("factura_id", "orden", name="uq_linea_factura_factura_orden"),
        CheckConstraint(
            "cantidad >= 0 AND precio_unitario >= 0 AND monto >= 0",
            name="ck_linea_factura_montos",
        ),
        Index("ix_linea_factura_factura", "factura_id"),
        Index("ix_linea_factura_producto", "producto_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    factura_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("factura.id", ondelete="CASCADE"), nullable=False
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(100), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_unidad: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    descuento_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    gravada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    unidades_por_caja: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cobrar_por: Mapped[str | None] = mapped_column(String(30), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("producto.id"), nullable=True
    )

    factura: Mapped["Factura"] = relationship("Factura", back_populates="lineas")
    producto: Mapped[Optional["Producto"]] = relationship(
        "Producto", back_populates="lineas_factura"
    )


class Categoria(Base):
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    productos: Mapped[list["Producto"]] = relationship(
        "Producto", back_populates="categoria"
    )


class Producto(TimestampMixin, Base):
    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_producto_sku"),
        Index("ix_producto_categoria", "categoria_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    categoria_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("categoria.id"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descripcion_corta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    imagen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    precio_caja: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_media_caja: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    permite_media_caja: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    precio_unidad: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    precio_consumidor: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    unidades_por_caja: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aplica_itbms: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    estado_activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    categoria: Mapped[Optional["Categoria"]] = relationship(
        "Categoria", back_populates="productos"
    )
    lineas_factura: Mapped[list["LineaFactura"]] = relationship(
        "LineaFactura", back_populates="producto"
    )
    lineas_pedido: Mapped[list["LineaPedidoB2B"]] = relationship(
        "LineaPedidoB2B", back_populates="producto"
    )


class ClienteB2B(Base):
    __tablename__ = "cliente_b2b"
    __table_args__ = (UniqueConstraint("ruc", name="uq_cliente_b2b_ruc"),)

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    nombre_empresa: Mapped[str] = mapped_column(String(200), nullable=False)
    ruc: Mapped[str] = mapped_column(String(40), nullable=False)
    email_contacto: Mapped[str | None] = mapped_column(String(254), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    pedidos: Mapped[list["PedidoB2B"]] = relationship(
        "PedidoB2B", back_populates="cliente"
    )


class PedidoB2B(TimestampMixin, Base):
    __tablename__ = "pedido_b2b"
    __table_args__ = (
        Index("ix_pedido_b2b_cliente", "cliente_id"),
        Index("ix_pedido_b2b_factura_generada", "factura_generada_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("cliente_b2b.id"), nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDIENTE", server_default="PENDIENTE"
    )
    total_estimado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    factura_generada_id: Mapped[int | None] = mapped_column(
        BIGINT, nullable=True, comment="Referencia debil a factura. Sin FK y sin UNIQUE."
    )

    cliente: Mapped["ClienteB2B"] = relationship(
        "ClienteB2B", back_populates="pedidos"
    )
    lineas: Mapped[list["LineaPedidoB2B"]] = relationship(
        "LineaPedidoB2B", back_populates="pedido", cascade="all, delete-orphan"
    )


class LineaPedidoB2B(Base):
    __tablename__ = "linea_pedido_b2b"
    __table_args__ = (
        UniqueConstraint("pedido_id", "orden", name="uq_linea_pedido_b2b_pedido_orden"),
        Index("ix_linea_pedido_pedido", "pedido_id"),
        Index("ix_linea_pedido_producto", "producto_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("pedido_b2b.id"), nullable=False
    )
    producto_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("producto.id"), nullable=False
    )
    tipo_empaque: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)

    pedido: Mapped["PedidoB2B"] = relationship("PedidoB2B", back_populates="lineas")
    producto: Mapped["Producto"] = relationship(
        "Producto", back_populates="lineas_pedido"
    )
