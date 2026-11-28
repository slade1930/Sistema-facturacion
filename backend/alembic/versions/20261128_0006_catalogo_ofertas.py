"""catálogo con marca, presentación y descuento

Revision ID: 20261128_0006
Revises: 20261127_0005
Create Date: 2026-11-28

Agrega solo etiquetas de producto y el descuento por producto. No toca precios,
ITBMS, serie ni código de verificación.
"""

from alembic import op
import sqlalchemy as sa

revision = "20261128_0006"
down_revision = "20261127_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("producto", sa.Column("marca", sa.String(100), nullable=True))
    op.add_column(
        "producto", sa.Column("presentacion", sa.String(50), nullable=True)
    )
    op.add_column(
        "producto",
        sa.Column(
            "descuento_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.create_check_constraint(
        "ck_producto_descuento",
        "producto",
        "descuento_pct >= 0 AND descuento_pct <= 90",
    )


def downgrade():
    op.drop_constraint("ck_producto_descuento", "producto", type_="check")
    op.drop_column("producto", "descuento_pct")
    op.drop_column("producto", "presentacion")
    op.drop_column("producto", "marca")
