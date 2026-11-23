from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Gente, solo las fechas que realmente están en el esquema oficial.

    Las comparten producto y pedido_b2b: fecha_creacion y fecha_actualizacion,
    mismos tipos y mismo server_default. Nada de created_at/updated_at inventados.
    """

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
