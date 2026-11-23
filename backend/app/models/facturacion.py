from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
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
from sqlalchemy.orm import relationship

from app.db.base import Base

BIGINT = BigInteger().with_variant(Integer, "sqlite")


class ConfiguracionNegocio(Base):
    __tablename__ = "configuracion_negocio"
    id = Column(BIGINT, primary_key=True)
    empresa_nombre = Column(String(150), nullable=False)
    empresa_ruc = Column(String(40), nullable=False, unique=True)
    mostrar_ruc = Column(Boolean, nullable=False, default=False, server_default="false")
    empresa_direccion = Column(Text)
    empresa_correo = Column(String(254))
    empresa_telefono = Column(String(60))
    logo = Column(String(100))
    color_principal = Column(String(7))
    color_barra_factura = Column(String(7))
    color_tabla = Column(String(7))
    datos_bancarios = Column(Text)
    notas_predeterminadas = Column(Text)
    actualizado = Column(
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

    id = Column(BIGINT, primary_key=True)
    anio = Column(Integer, nullable=False)
    ultimo_numero = Column(Integer, nullable=False, default=0, server_default="0")


class ContadorOrdenCompra(Base):
    __tablename__ = "contador_orden_compra"
    __table_args__ = (
        UniqueConstraint("anio", name="uq_contador_orden_compra_anio"),
        CheckConstraint("anio BETWEEN 1900 AND 9999", name="ck_contador_orden_compra_anio"),
        CheckConstraint("ultimo_numero >= 0", name="ck_contador_orden_compra_ultimo"),
    )

    id = Column(BIGINT, primary_key=True)
    anio = Column(Integer, nullable=False)
    ultimo_numero = Column(Integer, nullable=False, default=0, server_default="0")


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

    id = Column(BIGINT, primary_key=True)
    numero_serie = Column(String(20), nullable=False, unique=True)
    codigo_verificacion = Column(String(12), nullable=False, unique=True)
    fecha = Column(Date, nullable=False)

    cliente_nombre = Column(String(200), nullable=False)
    cliente_ruc = Column(String(40))
    mostrar_ruc = Column(Boolean, nullable=False, default=False, server_default="false")
    cliente_direccion = Column(String(250))
    cliente_telefono = Column(String(60))
    cliente_correo = Column(String(254))
    sucursal = Column(String(150))
    vendedor = Column(String(150))
    orden_compra = Column(String(60))
    condicion_pago = Column(String(30))
    portes = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    notas = Column(Text)

    subtotal = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    descuento_total = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    base_gravada = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    base_exenta = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    itbms = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    total = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )

    estado = Column(String(15), nullable=False, default="EMITIDA", server_default="EMITIDA")
    fecha_creacion = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_anulacion = Column(DateTime(timezone=True))

    lineas = relationship(
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

    id = Column(BIGINT, primary_key=True)
    factura_id = Column(
        BIGINT, ForeignKey("factura.id", ondelete="CASCADE"), nullable=False
    )
    orden = Column(Integer, nullable=False)
    descripcion = Column(String(300), nullable=False)
    codigo_barras = Column(String(100))
    categoria = Column(String(120))
    cantidad = Column(Numeric(14, 2), nullable=False)
    precio_unitario = Column(Numeric(14, 2), nullable=False)
    precio_unidad = Column(Numeric(14, 2))
    descuento_pct = Column(
        Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    gravada = Column(Boolean, nullable=False, default=False, server_default="false")
    unidades_por_caja = Column(Integer)
    cobrar_por = Column(String(30))
    monto = Column(Numeric(14, 2), nullable=False)
    producto_id = Column(BIGINT, ForeignKey("producto.id"), nullable=True)

    factura = relationship("Factura", back_populates="lineas")
    producto = relationship("Producto", back_populates="lineas_factura")


class Categoria(Base):
    __tablename__ = "categoria"

    id = Column(BIGINT, primary_key=True)
    nombre = Column(String(100), nullable=False, unique=True)

    productos = relationship("Producto", back_populates="categoria")


class Producto(Base):
    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_producto_sku"),
        Index("ix_producto_categoria", "categoria_id"),
    )

    id = Column(BIGINT, primary_key=True)
    categoria_id = Column(BIGINT, ForeignKey("categoria.id"), nullable=True)
    nombre = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=False)
    codigo_barras = Column(String(50))
    descripcion_corta = Column(String(500))
    imagen = Column(String(100))
    precio_caja = Column(Numeric(14, 2), nullable=False)
    precio_media_caja = Column(Numeric(14, 2))
    permite_media_caja = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    precio_unidad = Column(Numeric(14, 2))
    precio_consumidor = Column(Numeric(10, 2))
    unidades_por_caja = Column(Integer)
    aplica_itbms = Column(Boolean, nullable=False, default=True, server_default="true")
    estado_activo = Column(Boolean, nullable=False, default=True, server_default="true")
    fecha_creacion = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    categoria = relationship("Categoria", back_populates="productos")
    lineas_factura = relationship("LineaFactura", back_populates="producto")
    lineas_pedido = relationship("LineaPedidoB2B", back_populates="producto")


class ClienteB2B(Base):
    __tablename__ = "cliente_b2b"
    __table_args__ = (UniqueConstraint("ruc", name="uq_cliente_b2b_ruc"),)

    id = Column(BIGINT, primary_key=True)
    nombre_empresa = Column(String(200), nullable=False)
    ruc = Column(String(40), nullable=False)
    email_contacto = Column(String(254))
    telefono = Column(String(60))
    direccion = Column(Text)
    fecha_registro = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    activo = Column(Boolean, nullable=False, default=True, server_default="true")

    pedidos = relationship("PedidoB2B", back_populates="cliente")


class PedidoB2B(Base):
    __tablename__ = "pedido_b2b"
    __table_args__ = (
        Index("ix_pedido_b2b_cliente", "cliente_id"),
        Index("ix_pedido_b2b_factura_generada", "factura_generada_id"),
    )

    id = Column(BIGINT, primary_key=True)
    cliente_id = Column(
        BIGINT, ForeignKey("cliente_b2b.id"), nullable=False
    )
    fecha_creacion = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    estado = Column(String(30), nullable=False, default="PENDIENTE", server_default="PENDIENTE")
    total_estimado = Column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    notas = Column(Text)
    factura_generada_id = Column(
        BIGINT,
        comment="Referencia debil a factura. Sin FK y sin UNIQUE.",
    )

    cliente = relationship("ClienteB2B", back_populates="pedidos")
    lineas = relationship(
        "LineaPedidoB2B", back_populates="pedido", cascade="all, delete-orphan"
    )


class LineaPedidoB2B(Base):
    __tablename__ = "linea_pedido_b2b"
    __table_args__ = (
        UniqueConstraint("pedido_id", "orden", name="uq_linea_pedido_b2b_pedido_orden"),
        Index("ix_linea_pedido_pedido", "pedido_id"),
        Index("ix_linea_pedido_producto", "producto_id"),
    )

    id = Column(BIGINT, primary_key=True)
    pedido_id = Column(BIGINT, ForeignKey("pedido_b2b.id"), nullable=False)
    producto_id = Column(BIGINT, ForeignKey("producto.id"), nullable=False)
    tipo_empaque = Column(String(30))
    cantidad = Column(Numeric(14, 2), nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False)
    orden = Column(Integer, nullable=False)

    pedido = relationship("PedidoB2B", back_populates="lineas")
    producto = relationship("Producto", back_populates="lineas_pedido")
