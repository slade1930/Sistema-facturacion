# Gente, aquí van los modelos de facturación. Antes también estaban los de catálogo;
# los separé para respetar la estructura del proyecto, no cambia nada en la base de datos.

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

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
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    # Ojo: estos viven en catalogo.py. Solo para los tipos, así no hay import circular.
    from app.models.catalogo import PedidoB2B, Producto

BIGINT = BigInteger().with_variant(Integer, "sqlite")


# Gente, estos valores salen del sistema original (moisesroyal/Factura).
# Cada ENUM lleva su propio tipo en Postgres para que no choquen los dos "estado".
class CondicionPago(str, Enum):
    CONTADO = "contado"
    CREDITO = "credito"


class EstadoFactura(str, Enum):
    EMITIDA = "emitida"
    ANULADA = "anulada"
    EN_REVISION = "en_revision"


class CobrarPor(str, Enum):
    UNIDAD = "unidad"
    CAJA = "caja"


def _valores(enum_cls):
    # Ojo: guardamos el value en minúsculas, no el nombre del miembro.
    return [miembro.value for miembro in enum_cls]


class ConfiguracionNegocio(Base):
    __tablename__ = "configuracion_negocio"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    empresa_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    # Gente, el original no tenía UNIQUE acá: solo hay una fila de configuración.
    empresa_ruc: Mapped[str] = mapped_column(String(40), nullable=False)
    mostrar_ruc: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    empresa_direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    empresa_correo: Mapped[str | None] = mapped_column(String(254), nullable=True)
    empresa_telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color_principal: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#3A0088", server_default="#3A0088"
    )
    color_barra_factura: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#5B3A9E", server_default="#5B3A9E"
    )
    color_tabla: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#3A0088", server_default="#3A0088"
    )
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
        CheckConstraint("anio >= 0", name="ck_contador_serie_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_serie_ultimo"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ultimo_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class Factura(Base):
    __tablename__ = "factura"
    __table_args__ = (
        CheckConstraint(
            "estado <> 'anulada' OR fecha_anulacion IS NOT NULL",
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
    # Gente, el original NO ponía UNIQUE en el código de verificación.
    codigo_verificacion: Mapped[str] = mapped_column(String(12), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    cliente_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cliente_ruc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mostrar_ruc: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    cliente_direccion: Mapped[str | None] = mapped_column(String(250), nullable=True)
    cliente_telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cliente_correo: Mapped[str | None] = mapped_column(String(254), nullable=True)
    sucursal: Mapped[str | None] = mapped_column(String(150), nullable=True)
    vendedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    orden_compra: Mapped[str | None] = mapped_column(String(60), nullable=True)
    condicion_pago: Mapped[CondicionPago] = mapped_column(
        SAEnum(CondicionPago, name="condicion_pago", values_callable=_valores),
        nullable=False,
        default=CondicionPago.CONTADO,
        server_default=CondicionPago.CONTADO.value,
    )
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

    estado: Mapped[EstadoFactura] = mapped_column(
        SAEnum(EstadoFactura, name="estado_factura", values_callable=_valores),
        nullable=False,
        default=EstadoFactura.EMITIDA,
        server_default=EstadoFactura.EMITIDA.value,
    )
    # Sugerencia del modelo, no el estado emitida/anulada.
    en_revision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    puntaje_anomalia: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    motivo_anomalia: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_anulacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    lineas: Mapped[list["LineaFactura"]] = relationship(
        "LineaFactura", back_populates="factura", cascade="all, delete-orphan"
    )
    # Ojo: related_name del original era pedido_origen, 0..1 -> N pedidos.
    pedido_origen: Mapped[list["PedidoB2B"]] = relationship(
        "PedidoB2B", back_populates="factura_generada"
    )


class LineaFactura(Base):
    __tablename__ = "linea_factura"
    __table_args__ = (
        UniqueConstraint("factura_id", "orden", name="uq_linea_factura_factura_orden"),
        CheckConstraint(
            "precio_unitario >= 0 AND monto >= 0", name="ck_linea_factura_montos"
        ),
        CheckConstraint("cantidad >= 0.01", name="ck_linea_factura_cantidad"),
        CheckConstraint("unidades_por_caja >= 1", name="ck_linea_factura_unidades"),
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
    # Gente, esto lo ajusté para que coincida con el original: el default es True
    # porque el ITBMS del 7 % se aplica salvo que se diga lo contrario.
    gravada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    unidades_por_caja: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    cobrar_por: Mapped[CobrarPor] = mapped_column(
        SAEnum(CobrarPor, name="cobrar_por", values_callable=_valores),
        nullable=False,
        default=CobrarPor.UNIDAD,
        server_default=CobrarPor.UNIDAD.value,
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Ojo: el original usaba SET_NULL; borrar el producto no debe romper la línea.
    producto_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("producto.id", ondelete="SET NULL"), nullable=True
    )

    factura: Mapped["Factura"] = relationship("Factura", back_populates="lineas")
    producto: Mapped[Optional["Producto"]] = relationship(
        "Producto", back_populates="lineas_factura"
    )
