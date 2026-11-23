"""correcciones de fidelidad al sistema original

Revision ID: 20261123_0002
Revises: 20261123_0001
Create Date: 2026-11-23

Gente, la 0001 no se toca: acá solo ajustamos lo que estaba distinto del
sistema original (ENUM, defaults, ondelete, UNIQUE y CHECK).
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0002"
down_revision = "20261123_0001"
branch_labels = None
depends_on = None


CONDICION_PAGO = sa.Enum("contado", "credito", name="condicion_pago")
ESTADO_FACTURA = sa.Enum("emitida", "anulada", name="estado_factura")
COBRAR_POR = sa.Enum("unidad", "caja", name="cobrar_por")
ESTADO_PEDIDO = sa.Enum(
    "pendiente", "procesando", "facturado", "cancelado", name="estado_pedido_b2b"
)
TIPO_EMPAQUE = sa.Enum("caja", "media_caja", "unidad", name="tipo_empaque_b2b")

ENUMERADOS = (CONDICION_PAGO, ESTADO_FACTURA, COBRAR_POR, ESTADO_PEDIDO, TIPO_EMPAQUE)

COMENTARIO_VIEJO = "Referencia debil a factura. Sin FK y sin UNIQUE."
COMENTARIO_NUEVO = (
    "Referencia a factura. Sin UNIQUE: un pedido por factura no era requisito."
)


def upgrade():
    enlace = op.get_bind()

    # Gente, primero sacamos lo que estorba para convertir columnas.
    op.drop_constraint("ck_factura_estado", "factura", type_="check")
    op.drop_constraint("ck_factura_anulacion", "factura", type_="check")
    op.drop_constraint("ck_linea_factura_montos", "linea_factura", type_="check")
    op.drop_constraint("ck_contador_serie_anio", "contador_serie", type_="check")
    op.drop_constraint(
        "ck_contador_orden_compra_anio", "contador_orden_compra", type_="check"
    )
    op.drop_constraint(
        "uq_configuracion_negocio_empresa_ruc", "configuracion_negocio", type_="unique"
    )
    op.drop_constraint("uq_factura_codigo_verificacion", "factura", type_="unique")

    for nombre, tabla in (
        ("fk_linea_factura_producto_id_producto", "linea_factura"),
        ("fk_producto_categoria_id_categoria", "producto"),
        ("fk_pedido_b2b_cliente_id_cliente_b2b", "pedido_b2b"),
        ("fk_linea_pedido_b2b_pedido_id_pedido_b2b", "linea_pedido_b2b"),
        ("fk_linea_pedido_b2b_producto_id_producto", "linea_pedido_b2b"),
    ):
        op.drop_constraint(nombre, tabla, type_="foreignkey")

    # Ojo: los defaults viejos (EMITIDA, PENDIENTE, false, 0.00) no se pueden
    # convertir directo al tipo ENUM, así que primero los quitamos.
    for tabla, columna, tipo in (
        ("factura", "estado", sa.String(15)),
        ("pedido_b2b", "estado", sa.String(30)),
        ("linea_factura", "gravada", sa.Boolean()),
        ("factura", "mostrar_ruc", sa.Boolean()),
        ("configuracion_negocio", "mostrar_ruc", sa.Boolean()),
        ("configuracion_negocio", "color_principal", sa.String(7)),
        ("configuracion_negocio", "color_barra_factura", sa.String(7)),
        ("configuracion_negocio", "color_tabla", sa.String(7)),
        ("linea_factura", "unidades_por_caja", sa.Integer()),
        ("producto", "unidades_por_caja", sa.Integer()),
    ):
        op.alter_column(tabla, columna, existing_type=tipo, server_default=None)

    # No hay datos reales todavía, pero si quedó algo raro lo dejamos en un
    # valor válido antes de poner NOT NULL y convertir a ENUM.
    op.execute(
        "UPDATE factura SET condicion_pago = 'contado' WHERE condicion_pago IS NULL"
    )
    op.execute(
        "UPDATE linea_factura SET cobrar_por = 'unidad' WHERE cobrar_por IS NULL"
    )
    op.execute(
        "UPDATE linea_pedido_b2b SET tipo_empaque = 'caja' WHERE tipo_empaque IS NULL"
    )
    op.execute(
        "UPDATE configuracion_negocio SET color_principal = '#3A0088' "
        "WHERE color_principal IS NULL"
    )
    op.execute(
        "UPDATE configuracion_negocio SET color_barra_factura = '#5B3A9E' "
        "WHERE color_barra_factura IS NULL"
    )
    op.execute(
        "UPDATE configuracion_negocio SET color_tabla = '#3A0088' "
        "WHERE color_tabla IS NULL"
    )
    op.execute(
        "UPDATE linea_factura SET unidades_por_caja = 1 "
        "WHERE unidades_por_caja IS NULL"
    )
    op.execute(
        "UPDATE producto SET unidades_por_caja = 1 WHERE unidades_por_caja IS NULL"
    )
    # Gente, estos dos también eran NOT NULL en el original y vinieron NULL de la 0001.
    op.execute("UPDATE producto SET precio_unidad = 0.00 WHERE precio_unidad IS NULL")
    op.execute(
        "UPDATE cliente_b2b SET email_contacto = '' WHERE email_contacto IS NULL"
    )

    for enumerado in ENUMERADOS:
        enumerado.create(enlace, checkfirst=True)

    # Los valores guardados venían en MAYÚSCULA; lower() los deja como el original.
    op.alter_column(
        "factura",
        "condicion_pago",
        existing_type=sa.String(30),
        type_=CONDICION_PAGO,
        nullable=False,
        server_default="contado",
        postgresql_using="lower(condicion_pago)::condicion_pago",
    )
    op.alter_column(
        "factura",
        "estado",
        existing_type=sa.String(15),
        type_=ESTADO_FACTURA,
        nullable=False,
        server_default="emitida",
        postgresql_using="lower(estado)::estado_factura",
    )
    op.alter_column(
        "linea_factura",
        "cobrar_por",
        existing_type=sa.String(30),
        type_=COBRAR_POR,
        nullable=False,
        server_default="unidad",
        postgresql_using="lower(cobrar_por)::cobrar_por",
    )
    op.alter_column(
        "pedido_b2b",
        "estado",
        existing_type=sa.String(30),
        type_=ESTADO_PEDIDO,
        nullable=False,
        server_default="pendiente",
        postgresql_using="lower(estado)::estado_pedido_b2b",
    )
    op.alter_column(
        "linea_pedido_b2b",
        "tipo_empaque",
        existing_type=sa.String(30),
        type_=TIPO_EMPAQUE,
        nullable=False,
        server_default="caja",
        postgresql_using="lower(tipo_empaque)::tipo_empaque_b2b",
    )

    # Defaults que faltaban y columnas que el original no permitía dejar NULL.
    for tabla, columna, tipo, valor in (
        ("linea_factura", "gravada", sa.Boolean(), "true"),
        ("factura", "mostrar_ruc", sa.Boolean(), "true"),
        ("configuracion_negocio", "mostrar_ruc", sa.Boolean(), "true"),
        ("configuracion_negocio", "color_principal", sa.String(7), "#3A0088"),
        ("configuracion_negocio", "color_barra_factura", sa.String(7), "#5B3A9E"),
        ("configuracion_negocio", "color_tabla", sa.String(7), "#3A0088"),
        ("linea_factura", "unidades_por_caja", sa.Integer(), "1"),
        ("producto", "unidades_por_caja", sa.Integer(), "1"),
    ):
        op.alter_column(
            tabla, columna, existing_type=tipo, nullable=False, server_default=valor
        )
    op.alter_column(
        "producto",
        "categoria_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "producto",
        "precio_unidad",
        existing_type=sa.Numeric(14, 2),
        nullable=False,
    )
    op.alter_column(
        "cliente_b2b",
        "email_contacto",
        existing_type=sa.String(254),
        nullable=False,
    )

    # CHECK del original: PositiveInteger es >= 0, no un rango 1900..9999.
    for tabla in ("contador_serie", "contador_orden_compra"):
        op.create_check_constraint(
            f"ck_{tabla}_anio", tabla, "anio >= 0"
        )
    op.create_check_constraint(
        "ck_factura_anulacion",
        "factura",
        "estado <> 'anulada' OR fecha_anulacion IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_linea_factura_montos", "linea_factura", "precio_unitario >= 0 AND monto >= 0"
    )
    op.create_check_constraint(
        "ck_linea_factura_cantidad", "linea_factura", "cantidad >= 0.01"
    )
    op.create_check_constraint(
        "ck_linea_factura_unidades", "linea_factura", "unidades_por_caja >= 1"
    )
    op.create_check_constraint(
        "ck_producto_unidades", "producto", "unidades_por_caja >= 1"
    )

    # PROTECT de Django = RESTRICT acá; SET_NULL y CASCADE se mantienen igual.
    op.create_foreign_key(
        "fk_linea_factura_producto_id_producto",
        "linea_factura",
        "producto",
        ["producto_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_producto_categoria_id_categoria",
        "producto",
        "categoria",
        ["categoria_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pedido_b2b_cliente_id_cliente_b2b",
        "pedido_b2b",
        "cliente_b2b",
        ["cliente_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_linea_pedido_b2b_pedido_id_pedido_b2b",
        "linea_pedido_b2b",
        "pedido_b2b",
        ["pedido_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_linea_pedido_b2b_producto_id_producto",
        "linea_pedido_b2b",
        "producto",
        ["producto_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Ojo: aquí NO va UNIQUE en factura_generada_id, así estaba en el original.
    op.create_foreign_key(
        "fk_pedido_b2b_factura_generada_id_factura",
        "pedido_b2b",
        "factura",
        ["factura_generada_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column(
        "pedido_b2b",
        "factura_generada_id",
        existing_type=sa.BigInteger(),
        comment=COMENTARIO_NUEVO,
        existing_comment=COMENTARIO_VIEJO,
    )


def downgrade():
    enlace = op.get_bind()

    op.alter_column(
        "pedido_b2b",
        "factura_generada_id",
        existing_type=sa.BigInteger(),
        comment=COMENTARIO_VIEJO,
        existing_comment=COMENTARIO_NUEVO,
    )
    op.drop_constraint(
        "fk_pedido_b2b_factura_generada_id_factura", "pedido_b2b", type_="foreignkey"
    )

    for nombre, tabla in (
        ("ck_producto_unidades", "producto"),
        ("ck_linea_factura_unidades", "linea_factura"),
        ("ck_linea_factura_cantidad", "linea_factura"),
        ("ck_linea_factura_montos", "linea_factura"),
        ("ck_factura_anulacion", "factura"),
        ("ck_contador_orden_compra_anio", "contador_orden_compra"),
        ("ck_contador_serie_anio", "contador_serie"),
    ):
        op.drop_constraint(nombre, tabla, type_="check")

    for nombre, tabla in (
        ("fk_linea_factura_producto_id_producto", "linea_factura"),
        ("fk_producto_categoria_id_categoria", "producto"),
        ("fk_pedido_b2b_cliente_id_cliente_b2b", "pedido_b2b"),
        ("fk_linea_pedido_b2b_pedido_id_pedido_b2b", "linea_pedido_b2b"),
        ("fk_linea_pedido_b2b_producto_id_producto", "linea_pedido_b2b"),
    ):
        op.drop_constraint(nombre, tabla, type_="foreignkey")
    op.create_foreign_key(
        "fk_linea_factura_producto_id_producto",
        "linea_factura",
        "producto",
        ["producto_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_producto_categoria_id_categoria",
        "producto",
        "categoria",
        ["categoria_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_pedido_b2b_cliente_id_cliente_b2b",
        "pedido_b2b",
        "cliente_b2b",
        ["cliente_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_linea_pedido_b2b_pedido_id_pedido_b2b",
        "linea_pedido_b2b",
        "pedido_b2b",
        ["pedido_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_linea_pedido_b2b_producto_id_producto",
        "linea_pedido_b2b",
        "producto",
        ["producto_id"],
        ["id"],
    )

    op.alter_column("producto", "categoria_id", existing_type=sa.BigInteger(), nullable=True)
    op.alter_column(
        "producto",
        "precio_unidad",
        existing_type=sa.Numeric(14, 2),
        nullable=True,
    )
    op.alter_column(
        "cliente_b2b",
        "email_contacto",
        existing_type=sa.String(254),
        nullable=True,
    )

    for tabla, columna, tipo, valor in (
        ("linea_factura", "gravada", sa.Boolean(), "false"),
        ("factura", "mostrar_ruc", sa.Boolean(), "false"),
        ("configuracion_negocio", "mostrar_ruc", sa.Boolean(), "false"),
        ("linea_factura", "unidades_por_caja", sa.Integer(), None),
        ("producto", "unidades_por_caja", sa.Integer(), None),
    ):
        op.alter_column(
            tabla,
            columna,
            existing_type=tipo,
            nullable=True,
            server_default=valor,
        )
    for columna in ("color_principal", "color_barra_factura", "color_tabla"):
        op.alter_column(
            "configuracion_negocio",
            columna,
            existing_type=sa.String(7),
            nullable=True,
            server_default=None,
        )

    # Volvemos a VARCHAR. Los valores quedan en minúscula; el original usaba
    # mayúscula en los CHECK, así que los volvemos a escribir antes de crearlos.
    op.alter_column(
        "factura",
        "condicion_pago",
        existing_type=CONDICION_PAGO,
        type_=sa.String(30),
        nullable=True,
        server_default=None,
        postgresql_using="condicion_pago::text",
    )
    op.alter_column(
        "factura",
        "estado",
        existing_type=ESTADO_FACTURA,
        type_=sa.String(15),
        nullable=False,
        server_default="EMITIDA",
        postgresql_using="upper(estado::text)",
    )
    op.alter_column(
        "linea_factura",
        "cobrar_por",
        existing_type=COBRAR_POR,
        type_=sa.String(30),
        nullable=True,
        server_default=None,
        postgresql_using="cobrar_por::text",
    )
    op.alter_column(
        "pedido_b2b",
        "estado",
        existing_type=ESTADO_PEDIDO,
        type_=sa.String(30),
        nullable=False,
        server_default="PENDIENTE",
        postgresql_using="upper(estado::text)",
    )
    op.alter_column(
        "linea_pedido_b2b",
        "tipo_empaque",
        existing_type=TIPO_EMPAQUE,
        type_=sa.String(30),
        nullable=True,
        server_default=None,
        postgresql_using="tipo_empaque::text",
    )

    for enumerado in reversed(ENUMERADOS):
        enumerado.drop(enlace, checkfirst=True)

    op.create_check_constraint(
        "ck_contador_serie_anio",
        "contador_serie",
        "anio BETWEEN 1900 AND 9999",
    )
    op.create_check_constraint(
        "ck_contador_orden_compra_anio",
        "contador_orden_compra",
        "anio BETWEEN 1900 AND 9999",
    )
    op.create_check_constraint(
        "ck_factura_estado", "factura", "estado IN ('EMITIDA','ANULADA')"
    )
    op.create_check_constraint(
        "ck_factura_anulacion",
        "factura",
        "estado <> 'ANULADA' OR fecha_anulacion IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_linea_factura_montos",
        "linea_factura",
        "precio_unitario >= 0 AND monto >= 0",
    )
    op.create_unique_constraint(
        "uq_configuracion_negocio_empresa_ruc",
        "configuracion_negocio",
        ["empresa_ruc"],
    )
    op.create_unique_constraint(
        "uq_factura_codigo_verificacion", "factura", ["codigo_verificacion"]
    )
