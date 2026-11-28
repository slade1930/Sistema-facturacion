"""portal de empresas

Revision ID: 20261127_0005
Revises: 20261127_0004
Create Date: 2026-11-27

Cuentas, sesiones, sectores, inventario y auditoría para la etapa A.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261127_0005"
down_revision = "20261127_0004"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer, "sqlite")

SECTOR = sa.Enum(
    "tecnologia", "turismo", "supermercado",
    name="sector_empresa", create_type=False,
)
ROL = sa.Enum("admin", "empresa", name="rol_cuenta", create_type=False)
MOVIMIENTO = sa.Enum(
    "entrada", "salida", "ajuste",
    name="tipo_movimiento_inventario", create_type=False,
)


def upgrade():
    op.execute("CREATE TYPE sector_empresa AS ENUM ('tecnologia', 'turismo', 'supermercado')")
    op.execute("CREATE TYPE rol_cuenta AS ENUM ('admin', 'empresa')")
    op.execute("CREATE TYPE tipo_movimiento_inventario AS ENUM ('entrada', 'salida', 'ajuste')")

    op.add_column("categoria", sa.Column("sector", SECTOR, nullable=True))
    op.add_column("cliente_b2b", sa.Column("sucursal", sa.String(150), nullable=True))
    op.add_column("cliente_b2b", sa.Column("sector", SECTOR, nullable=True))

    op.add_column(
        "factura",
        sa.Column(
            "cliente_id",
            BIGINT,
            sa.ForeignKey(
                "cliente_b2b.id",
                name="fk_factura_cliente_id_cliente_b2b",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_factura_cliente", "factura", ["cliente_id"])

    # El pedido ligado manda; si no hay pedido, solo un RUC exacto y único.
    op.execute(
        """
        UPDATE factura f
        SET cliente_id = (
            SELECT p.cliente_id FROM pedido_b2b p
            WHERE p.factura_generada_id = f.id
            ORDER BY p.id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM pedido_b2b p WHERE p.factura_generada_id = f.id
        )
        """
    )
    op.execute(
        """
        UPDATE factura f
        SET cliente_id = c.id
        FROM cliente_b2b c
        WHERE f.cliente_id IS NULL
          AND f.cliente_ruc IS NOT NULL
          AND c.ruc = f.cliente_ruc
          AND (SELECT COUNT(*) FROM cliente_b2b c2 WHERE c2.ruc = f.cliente_ruc) = 1
        """
    )

    op.add_column(
        "pedido_b2b",
        sa.Column("clave_idempotencia", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_pedido_b2b_cliente_idempotencia",
        "pedido_b2b",
        ["cliente_id", "clave_idempotencia"],
    )

    op.create_table(
        "cuenta",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("nombre_usuario", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", ROL, nullable=False),
        sa.Column(
            "cliente_id",
            BIGINT,
            sa.ForeignKey(
                "cliente_b2b.id",
                name="fk_cuenta_cliente_id_cliente_b2b",
                ondelete="CASCADE",
            ),
            nullable=True,
        ),
        sa.Column(
            "activo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "debe_cambiar_clave",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("nombre_usuario", name="uq_cuenta_nombre_usuario"),
        sa.CheckConstraint(
            "(rol = 'empresa' AND cliente_id IS NOT NULL) "
            "OR (rol = 'admin' AND cliente_id IS NULL)",
            name="ck_cuenta_rol_cliente",
        ),
    )
    op.create_index("ix_cuenta_cliente", "cuenta", ["cliente_id"])

    op.create_table(
        "sesion",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column(
            "cuenta_id",
            BIGINT,
            sa.ForeignKey(
                "cuenta.id", name="fk_sesion_cuenta_id_cuenta", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "ultima_actividad",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revocada", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.UniqueConstraint("token_hash", name="uq_sesion_token_hash"),
    )
    op.create_index("ix_sesion_cuenta", "sesion", ["cuenta_id"])

    op.create_table(
        "auditoria",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "cuenta_id",
            BIGINT,
            sa.ForeignKey(
                "cuenta.id",
                name="fk_auditoria_cuenta_id_cuenta",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column("accion", sa.String(80), nullable=False),
        sa.Column("detalle", sa.String(500), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
    )
    op.create_index("ix_auditoria_fecha", "auditoria", ["fecha"])
    op.create_index("ix_auditoria_cuenta", "auditoria", ["cuenta_id"])

    op.create_table(
        "inventario",
        sa.Column(
            "producto_id",
            BIGINT,
            sa.ForeignKey(
                "producto.id",
                name="fk_inventario_producto_id_producto",
                ondelete="CASCADE",
            ),
            primary_key=True,
        ),
        sa.Column(
            "existencias",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column(
            "stock_minimo",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("existencias >= 0", name="ck_inventario_existencias"),
        sa.CheckConstraint("stock_minimo >= 0", name="ck_inventario_minimo"),
    )

    op.create_table(
        "movimiento_inventario",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            BIGINT,
            sa.ForeignKey(
                "producto.id",
                name="fk_movimiento_inventario_producto_id_producto",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("tipo", MOVIMIENTO, nullable=False),
        sa.Column("cantidad", sa.Numeric(14, 2), nullable=False),
        sa.Column("motivo", sa.String(200), nullable=False),
        sa.Column(
            "factura_id",
            BIGINT,
            sa.ForeignKey(
                "factura.id",
                name="fk_movimiento_inventario_factura_id_factura",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "cuenta_id",
            BIGINT,
            sa.ForeignKey(
                "cuenta.id",
                name="fk_movimiento_inventario_cuenta_id_cuenta",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.CheckConstraint(
            "cantidad > 0", name="ck_movimiento_inventario_cantidad"
        ),
    )
    op.create_index(
        "ix_movimiento_inventario_producto", "movimiento_inventario", ["producto_id"]
    )
    op.create_index(
        "ix_movimiento_inventario_factura", "movimiento_inventario", ["factura_id"]
    )


def downgrade():
    op.drop_index("ix_movimiento_inventario_factura", "movimiento_inventario")
    op.drop_index("ix_movimiento_inventario_producto", "movimiento_inventario")
    op.drop_table("movimiento_inventario")
    op.drop_table("inventario")
    op.drop_table("auditoria")
    op.drop_table("sesion")
    op.drop_table("cuenta")
    op.drop_constraint(
        "uq_pedido_b2b_cliente_idempotencia",
        "pedido_b2b",
        type_="unique",
    )
    op.drop_column("pedido_b2b", "clave_idempotencia")
    op.drop_column("factura", "cliente_id")
    op.drop_column("cliente_b2b", "sector")
    op.drop_column("cliente_b2b", "sucursal")
    op.drop_column("categoria", "sector")
    op.execute("DROP TYPE tipo_movimiento_inventario")
    op.execute("DROP TYPE rol_cuenta")
    op.execute("DROP TYPE sector_empresa")
