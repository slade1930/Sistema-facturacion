"""nucleo de facturacion segun draw.io

Revision ID: 20261123_0001
Revises:
Create Date: 2026-11-23

"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "configuracion_negocio",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("empresa_nombre", sa.String(length=150), nullable=False),
        sa.Column("empresa_ruc", sa.String(length=40), nullable=False),
        sa.Column("mostrar_ruc", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("empresa_direccion", sa.Text(), nullable=True),
        sa.Column("empresa_correo", sa.String(length=254), nullable=True),
        sa.Column("empresa_telefono", sa.String(length=60), nullable=True),
        sa.Column("logo", sa.String(length=100), nullable=True),
        sa.Column("color_principal", sa.String(length=7), nullable=True),
        sa.Column("color_barra_factura", sa.String(length=7), nullable=True),
        sa.Column("color_tabla", sa.String(length=7), nullable=True),
        sa.Column("datos_bancarios", sa.Text(), nullable=True),
        sa.Column("notas_predeterminadas", sa.Text(), nullable=True),
        sa.Column("actualizado", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_configuracion_negocio"),
        sa.UniqueConstraint("empresa_ruc", name="uq_configuracion_negocio_empresa_ruc"),
    )
    op.create_table(
        "contador_serie",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("ultimo_numero", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("anio BETWEEN 1900 AND 9999", name="ck_contador_serie_anio"),
        sa.CheckConstraint("ultimo_numero >= 0", name="ck_contador_serie_ultimo"),
        sa.PrimaryKeyConstraint("id", name="pk_contador_serie"),
        sa.UniqueConstraint("anio", name="uq_contador_serie_anio"),
    )
    op.create_table(
        "contador_orden_compra",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("ultimo_numero", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("anio BETWEEN 1900 AND 9999",
                           name="ck_contador_orden_compra_anio"),
        sa.CheckConstraint("ultimo_numero >= 0",
                           name="ck_contador_orden_compra_ultimo"),
        sa.PrimaryKeyConstraint("id", name="pk_contador_orden_compra"),
        sa.UniqueConstraint("anio", name="uq_contador_orden_compra_anio"),
    )
    op.create_table(
        "categoria",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_categoria"),
        sa.UniqueConstraint("nombre", name="uq_categoria_nombre"),
    )
    op.create_table(
        "producto",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("categoria_id", sa.BigInteger(), nullable=True),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("codigo_barras", sa.String(length=50), nullable=True),
        sa.Column("descripcion_corta", sa.String(length=500), nullable=True),
        sa.Column("imagen", sa.String(length=100), nullable=True),
        sa.Column("precio_caja", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("precio_media_caja", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("permite_media_caja", sa.Boolean(), server_default="false",
                  nullable=False),
        sa.Column("precio_unidad", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("precio_consumidor", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("unidades_por_caja", sa.Integer(), nullable=True),
        sa.Column("aplica_itbms", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("estado_activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["categoria_id"], ["categoria.id"],
                                name="fk_producto_categoria_id_categoria"),
        sa.PrimaryKeyConstraint("id", name="pk_producto"),
        sa.UniqueConstraint("sku", name="uq_producto_sku"),
    )
    op.create_index("ix_producto_categoria", "producto", ["categoria_id"])
    op.create_table(
        "factura",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("numero_serie", sa.String(length=20), nullable=False),
        sa.Column("codigo_verificacion", sa.String(length=12), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cliente_nombre", sa.String(length=200), nullable=False),
        sa.Column("cliente_ruc", sa.String(length=40), nullable=True),
        sa.Column("mostrar_ruc", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("cliente_direccion", sa.String(length=250), nullable=True),
        sa.Column("cliente_telefono", sa.String(length=60), nullable=True),
        sa.Column("cliente_correo", sa.String(length=254), nullable=True),
        sa.Column("sucursal", sa.String(length=150), nullable=True),
        sa.Column("vendedor", sa.String(length=150), nullable=True),
        sa.Column("orden_compra", sa.String(length=60), nullable=True),
        sa.Column("condicion_pago", sa.String(length=30), nullable=True),
        sa.Column("portes", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("descuento_total", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("base_gravada", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("base_exenta", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("itbms", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("estado", sa.String(length=15),
                  server_default="EMITIDA", nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_anulacion", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("estado IN ('EMITIDA','ANULADA')",
                           name="ck_factura_estado"),
        sa.CheckConstraint("estado <> 'ANULADA' OR fecha_anulacion IS NOT NULL",
                           name="ck_factura_anulacion"),
        sa.CheckConstraint(
            "subtotal >= 0 AND descuento_total >= 0 AND base_gravada >= 0 "
            "AND base_exenta >= 0 AND portes >= 0 AND itbms >= 0 AND total >= 0",
            name="ck_factura_totales",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_factura"),
        sa.UniqueConstraint("numero_serie", name="uq_factura_numero_serie"),
        sa.UniqueConstraint("codigo_verificacion", name="uq_factura_codigo_verificacion"),
    )
    op.create_index("ix_factura_fecha", "factura", ["fecha"])
    op.create_table(
        "linea_factura",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("factura_id", sa.BigInteger(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.String(length=300), nullable=False),
        sa.Column("codigo_barras", sa.String(length=100), nullable=True),
        sa.Column("categoria", sa.String(length=120), nullable=True),
        sa.Column("cantidad", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("precio_unidad", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("descuento_pct", sa.Numeric(precision=6, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("gravada", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("unidades_por_caja", sa.Integer(), nullable=True),
        sa.Column("cobrar_por", sa.String(length=30), nullable=True),
        sa.Column("monto", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("cantidad >= 0 AND precio_unitario >= 0 AND monto >= 0",
                           name="ck_linea_factura_montos"),
        sa.ForeignKeyConstraint(["factura_id"], ["factura.id"],
                                name="fk_linea_factura_factura_id_factura",
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["producto_id"], ["producto.id"],
                                name="fk_linea_factura_producto_id_producto"),
        sa.PrimaryKeyConstraint("id", name="pk_linea_factura"),
        sa.UniqueConstraint("factura_id", "orden",
                            name="uq_linea_factura_factura_orden"),
    )
    op.create_index("ix_linea_factura_factura", "linea_factura", ["factura_id"])
    op.create_index("ix_linea_factura_producto", "linea_factura", ["producto_id"])
    op.create_table(
        "cliente_b2b",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("nombre_empresa", sa.String(length=200), nullable=False),
        sa.Column("ruc", sa.String(length=40), nullable=False),
        sa.Column("email_contacto", sa.String(length=254), nullable=True),
        sa.Column("telefono", sa.String(length=60), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cliente_b2b"),
        sa.UniqueConstraint("ruc", name="uq_cliente_b2b_ruc"),
    )
    op.create_table(
        "pedido_b2b",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("estado", sa.String(length=30),
                  server_default="PENDIENTE", nullable=False),
        sa.Column("total_estimado", sa.Numeric(precision=14, scale=2),
                  server_default="0.00", nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("factura_generada_id", sa.BigInteger(), nullable=True,
                  comment="Referencia debil a factura. Sin FK y sin UNIQUE."),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente_b2b.id"],
                                name="fk_pedido_b2b_cliente_id_cliente_b2b"),
        sa.PrimaryKeyConstraint("id", name="pk_pedido_b2b"),
    )
    op.create_index("ix_pedido_b2b_cliente", "pedido_b2b", ["cliente_id"])
    op.create_index("ix_pedido_b2b_factura_generada", "pedido_b2b",
                    ["factura_generada_id"])
    op.create_table(
        "linea_pedido_b2b",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("pedido_id", sa.BigInteger(), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_empaque", sa.String(length=30), nullable=True),
        sa.Column("cantidad", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedido_b2b.id"],
                                name="fk_linea_pedido_b2b_pedido_id_pedido_b2b"),
        sa.ForeignKeyConstraint(["producto_id"], ["producto.id"],
                                name="fk_linea_pedido_b2b_producto_id_producto"),
        sa.PrimaryKeyConstraint("id", name="pk_linea_pedido_b2b"),
        sa.UniqueConstraint("pedido_id", "orden",
                            name="uq_linea_pedido_b2b_pedido_orden"),
    )
    op.create_index("ix_linea_pedido_pedido", "linea_pedido_b2b", ["pedido_id"])
    op.create_index("ix_linea_pedido_producto", "linea_pedido_b2b", ["producto_id"])

def downgrade():
    op.drop_index("ix_linea_pedido_producto", table_name="linea_pedido_b2b")
    op.drop_index("ix_linea_pedido_pedido", table_name="linea_pedido_b2b")
    op.drop_table("linea_pedido_b2b")
    op.drop_index("ix_pedido_b2b_factura_generada", table_name="pedido_b2b")
    op.drop_index("ix_pedido_b2b_cliente", table_name="pedido_b2b")
    op.drop_table("pedido_b2b")
    op.drop_table("cliente_b2b")
    op.drop_index("ix_linea_factura_producto", table_name="linea_factura")
    op.drop_index("ix_linea_factura_factura", table_name="linea_factura")
    op.drop_table("linea_factura")
    op.drop_index("ix_factura_fecha", table_name="factura")
    op.drop_table("factura")
    op.drop_index("ix_producto_categoria", table_name="producto")
    op.drop_table("producto")
    op.drop_table("categoria")
    op.drop_table("contador_orden_compra")
    op.drop_table("contador_serie")
    op.drop_table("configuracion_negocio")