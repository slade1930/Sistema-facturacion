# Gente, aquí van los modelos de catálogo y pedidos B2B. Antes estaban en
# facturacion.py; los separé para respetar la estructura del proyecto, no cambia nada en la base de datos.

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    # Ojo: estos viven en facturacion.py. Solo para los tipos, sin import circular.
    from app.models.facturacion import Factura, LineaFactura

BIGINT = BigInteger().with_variant(Integer, "sqlite")


class EstadoPedido(str, Enum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    FACTURADO = "facturado"
    CANCELADO = "cancelado"


class TipoEmpaque(str, Enum):
    CAJA = "caja"
    MEDIA_CAJA = "media_caja"
    UNIDAD = "unidad"


class SectorEmpresa(str, Enum):
    TECNOLOGIA = "tecnologia"
    TURISMO = "turismo"
    SUPERMERCADO = "supermercado"


def _valores(enum_cls):
    # Ojo: guardamos el value en minúsculas, no el nombre del miembro.
    return [miembro.value for miembro in enum_cls]


class Categoria(Base):
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    sector: Mapped[SectorEmpresa | None] = mapped_column(
        SAEnum(SectorEmpresa, name="sector_empresa", values_callable=_valores),
        nullable=True,
    )

    productos: Mapped[list["Producto"]] = relationship(
        "Producto", back_populates="categoria"
    )


class Producto(TimestampMixin, Base):
    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_producto_sku"),
        CheckConstraint("unidades_por_caja >= 1", name="ck_producto_unidades"),
        CheckConstraint(
            "descuento_pct >= 0 AND descuento_pct <= 90",
            name="ck_producto_descuento",
        ),
        Index("ix_producto_categoria", "categoria_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    # PROTECT en Django = RESTRICT en la base. Y la categoría era obligatoria.
    categoria_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("categoria.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descripcion_corta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    presentacion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imagen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    precio_caja: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_media_caja: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    permite_media_caja: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Gente, esto es NOT NULL porque así estaba en el original; faltaba en la primera versión.
    precio_unidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_consumidor: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    unidades_por_caja: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    descuento_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    aplica_itbms: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    estado_activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    categoria: Mapped["Categoria"] = relationship(
        "Categoria", back_populates="productos"
    )
    # Ojo: la línea de factura está en el otro archivo; va por nombre de clase.
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
    # Gente, esto es NOT NULL porque así estaba en el original; faltaba en la primera versión.
    email_contacto: Mapped[str] = mapped_column(String(254), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    sucursal: Mapped[str | None] = mapped_column(String(150), nullable=True)
    sector: Mapped[SectorEmpresa | None] = mapped_column(
        SAEnum(SectorEmpresa, name="sector_empresa", values_callable=_valores),
        nullable=True,
    )
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
        UniqueConstraint(
            "cliente_id",
            "clave_idempotencia",
            name="uq_pedido_b2b_cliente_idempotencia",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    # PROTECT en el original -> RESTRICT acá.
    cliente_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("cliente_b2b.id", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[EstadoPedido] = mapped_column(
        SAEnum(EstadoPedido, name="estado_pedido_b2b", values_callable=_valores),
        nullable=False,
        default=EstadoPedido.PENDIENTE,
        server_default=EstadoPedido.PENDIENTE.value,
    )
    total_estimado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Ojo: aquí NO va UNIQUE en factura_generada_id, así estaba en el original.
    # Ahora sí va la FK real (SET_NULL) y la relación 0..1 -> N.
    factura_generada_id: Mapped[int | None] = mapped_column(
        BIGINT,
        ForeignKey("factura.id", ondelete="SET NULL"),
        nullable=True,
        comment="Referencia a factura. Sin UNIQUE: un pedido por factura no era requisito.",
    )
    clave_idempotencia: Mapped[str | None] = mapped_column(String(64), nullable=True)

    cliente: Mapped["ClienteB2B"] = relationship(
        "ClienteB2B", back_populates="pedidos"
    )
    # Ojo: la factura está en el otro archivo; también va por nombre de clase.
    factura_generada: Mapped[Optional["Factura"]] = relationship(
        "Factura", back_populates="pedido_origen"
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
    # CASCADE en pedido, PROTECT -> RESTRICT en producto, según el original.
    pedido_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("pedido_b2b.id", ondelete="CASCADE"), nullable=False
    )
    producto_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("producto.id", ondelete="RESTRICT"), nullable=False
    )
    tipo_empaque: Mapped[TipoEmpaque] = mapped_column(
        SAEnum(TipoEmpaque, name="tipo_empaque_b2b", values_callable=_valores),
        nullable=False,
        default=TipoEmpaque.CAJA,
        server_default=TipoEmpaque.CAJA.value,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)

    pedido: Mapped["PedidoB2B"] = relationship("PedidoB2B", back_populates="lineas")
    producto: Mapped["Producto"] = relationship(
        "Producto", back_populates="lineas_pedido"
    )


class ContadorOrdenCompra(Base):
    __tablename__ = "contador_orden_compra"
    __table_args__ = (
        UniqueConstraint("anio", name="uq_contador_orden_compra_anio"),
        CheckConstraint("anio >= 0", name="ck_contador_orden_compra_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_orden_compra_ultimo"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
