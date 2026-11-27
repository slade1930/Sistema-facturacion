"""en_revision en factura

Revision ID: 20261127_0004
Revises: 20261123_0003
Create Date: 2026-11-27

La sugerencia del modelo se guarda en una columna booleana propia, sin
tocar el estado emitida/anulada ni el valor 'en_revision' del enum.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261127_0004"
down_revision = "20261123_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "factura",
        sa.Column(
            "en_revision",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade():
    op.drop_column("factura", "en_revision")
