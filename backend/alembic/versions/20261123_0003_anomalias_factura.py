"""anomalias en factura

Revision ID: 20261123_0003
Revises: 20261123_0002
Create Date: 2026-11-26

Agrega 'en_revision' al ENUM estado_factura y las columnas de anomalia
en factura. Tambien corrige dos CHECK que la 0002 dejo en MAYUSCULA
mientras el ENUM guarda valores en minuscula.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0003"
down_revision = "20261123_0002"
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL 12+ permite ADD VALUE dentro de transaccion. El valor nuevo
    # no se usa como literal de enum aca, solo se compara como texto.
    op.execute("ALTER TYPE estado_factura ADD VALUE IF NOT EXISTS 'en_revision'")

    op.add_column(
        "factura",
        sa.Column("puntaje_anomalia", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "factura",
        sa.Column("motivo_anomalia", sa.Text(), nullable=True),
    )

    # La 0002 creo este CHECK en MAYUSCULA. Se reemplaza por uno en minusculas
    # que ademas acepta el nuevo estado.
    op.drop_constraint("ck_factura_estado", "factura", type_="check")
    op.create_check_constraint(
        "ck_factura_estado",
        "factura",
        "estado::text IN ('emitida', 'anulada', 'en_revision')",
    )

    # Este tambien estaba en MAYUSCULA y no coincidia con el ENUM.
    op.drop_constraint("ck_factura_anulacion", "factura", type_="check")
    op.create_check_constraint(
        "ck_factura_anulacion",
        "factura",
        "estado <> 'anulada' OR fecha_anulacion IS NOT NULL",
    )


def downgrade():
    # Si hay facturas en revision, se dejan como emitidas antes de quitar el
    # valor del CHECK.
    op.execute("UPDATE factura SET estado = 'emitida' WHERE estado::text = 'en_revision'")

    op.drop_constraint("ck_factura_anulacion", "factura", type_="check")
    op.create_check_constraint(
        "ck_factura_anulacion",
        "factura",
        "estado <> 'anulada' OR fecha_anulacion IS NOT NULL",
    )

    op.drop_constraint("ck_factura_estado", "factura", type_="check")
    op.create_check_constraint(
        "ck_factura_estado",
        "factura",
        "estado::text IN ('emitida', 'anulada')",
    )

    op.drop_column("factura", "motivo_anomalia")
    op.drop_column("factura", "puntaje_anomalia")

    # El valor 'en_revision' se deja en el tipo ENUM: quitarlo obligaria a
    # recrear el tipo. Un nuevo upgrade es idempotente (IF NOT EXISTS).
