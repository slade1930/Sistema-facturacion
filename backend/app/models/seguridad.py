"""Cuenta, sesión y auditoría del portal de empresas. Empresa y admin; etapa A."""

from datetime import datetime
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
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.catalogo import ClienteB2B

BIGINT = BigInteger().with_variant(Integer, "sqlite")


def _valores(enum_cls):
    return [miembro.value for miembro in enum_cls]


class RolCuenta(str, Enum):
    ADMIN = "admin"
    EMPRESA = "empresa"


class Cuenta(Base):
    __tablename__ = "cuenta"
    __table_args__ = (
        UniqueConstraint("nombre_usuario", name="uq_cuenta_nombre_usuario"),
        CheckConstraint(
            "(rol = 'empresa' AND cliente_id IS NOT NULL) "
            "OR (rol = 'admin' AND cliente_id IS NULL)",
            name="ck_cuenta_rol_cliente",
        ),
        Index("ix_cuenta_cliente", "cliente_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolCuenta] = mapped_column(
        SAEnum(RolCuenta, name="rol_cuenta", values_callable=_valores),
        nullable=False,
    )
    cliente_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("cliente_b2b.id", ondelete="CASCADE"), nullable=True
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    debe_cambiar_clave: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ultimo_acceso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cliente: Mapped[Optional["ClienteB2B"]] = relationship("ClienteB2B")
    sesiones: Mapped[list["Sesion"]] = relationship(
        "Sesion", back_populates="cuenta", cascade="all, delete-orphan"
    )


class Sesion(Base):
    __tablename__ = "sesion"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_sesion_token_hash"),
        Index("ix_sesion_cuenta", "cuenta_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("cuenta.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ultima_actividad: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expira_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revocada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    cuenta: Mapped["Cuenta"] = relationship("Cuenta", back_populates="sesiones")


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_fecha", "fecha"),
        Index("ix_auditoria_cuenta", "cuenta_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cuenta_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("cuenta.id", ondelete="SET NULL"), nullable=True
    )
    accion: Mapped[str] = mapped_column(String(80), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
