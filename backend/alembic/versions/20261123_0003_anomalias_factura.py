"""anomalias en factura

Revision ID: 20261123_0003
Revises: 20261123_0002
Create Date: 2026-11-26

Agrega 'en_revision' al ENUM estado_factura y las columnas de anomalia
en factura. Lo del PR #12 estaba bien (tipos, modelo y pruebas); aca solo
se acomoda la migracion para que corra desde cero.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0003"
down_revision = "20261123_0002"
branch_labels = None
depends_on = None


def upgrade():
    # Gente, primero el valor del ENUM y con autocommit_block para que no se
    # enrede con la transacción de las columnas y los CHECK que lo usan. El
    # valor nuevo no se usa como literal aca, solo se compara como texto.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE estado_factura ADD VALUE IF NOT EXISTS 'en_revision'")

    op.add_column(
        "factura",
        sa.Column("puntaje_anomalia", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "factura",
        sa.Column("motivo_anomalia", sa.Text(), nullable=True),
    )

    # Gente, la 0002 no deja creada esta restricción; por eso se borra con
    # IF EXISTS antes de recrearla y la migración corre desde cero.
    op.execute("ALTER TABLE factura DROP CONSTRAINT IF EXISTS ck_factura_estado")
    op.create_check_constraint(
        "ck_factura_estado",
        "factura",
        "estado::text IN ('emitida', 'anulada', 'en_revision')",
    )

    # Esta sí quedó en la 0002, pero también se bora primero por si acaso.
    op.execute("ALTER TABLE factura DROP CONSTRAINT IF EXISTS ck_factura_anulacion")
    op.create_check_constraint(
        "ck_factura_anulacion",
        "factura",
        "estado <> 'anulada' OR fecha_anulacion IS NOT NULL",
    )


def downgrade():
    # Si hay facturas en revision, se dejan como emitidas antes de quitar el
    # valor del CHECK.
    op.execute("UPDATE factura SET estado = 'emitida' WHERE estado::text = 'en_revision'")

    # Gente, acá también IF EXISTS para no depender de que estén las dos.
    op.execute("ALTER TABLE factura DROP CONSTRAINT IF EXISTS ck_factura_anulacion")
    op.create_check_constraint(
        "ck_factura_anulacion",
        "factura",
        "estado <> 'anulada' OR fecha_anulacion IS NOT NULL",
    )

    # Ojo: después de la 0002 ck_factura_estado NO existía. Se bora y listo,
    # así la tabla queda con las mismas restricciones de ese revision.
    op.execute("ALTER TABLE factura DROP CONSTRAINT IF EXISTS ck_factura_estado")

    op.drop_column("factura", "motivo_anomalia")
    op.drop_column("factura", "puntaje_anomalia")

    # Gente, el valor 'en_revision' del ENUM NO se revierte: se queda en la
    # base y es esperado. Quitarlo obligaría a recrear el tipo, así que no lo
    # tocamos. Un nuevo upgrade es idempotente (IF NOT EXISTS).
