"""Consultas de cuentas, sesiones y auditoría. Portal; etapa A."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.seguridad import Auditoria, Cuenta, Sesion


class CuentasRepository:
    def __init__(self, db: Session):
        self.db = db

    def por_nombre_usuario(self, nombre_usuario: str) -> Cuenta | None:
        return self.db.scalar(
            select(Cuenta).where(Cuenta.nombre_usuario == nombre_usuario)
        )

    def por_id(self, cuenta_id: int) -> Cuenta | None:
        return self.db.get(Cuenta, cuenta_id)

    def crear(self, cuenta: Cuenta) -> Cuenta:
        self.db.add(cuenta)
        self.db.flush()
        return cuenta


class SesionesRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, sesion: Sesion) -> Sesion:
        self.db.add(sesion)
        self.db.flush()
        return sesion

    def por_token_hash(self, token_hash: str) -> Sesion | None:
        return self.db.scalar(select(Sesion).where(Sesion.token_hash == token_hash))

    def revocar(self, cuenta_id: int, excepto_hash: str | None = None) -> None:
        consulta = update(Sesion).where(
            Sesion.cuenta_id == cuenta_id, Sesion.revocada.is_(False)
        )
        if excepto_hash is not None:
            consulta = consulta.where(Sesion.token_hash != excepto_hash)
        self.db.execute(consulta.values(revocada=True))

    def revocar_token(self, token_hash: str) -> None:
        self.db.execute(
            update(Sesion)
            .where(Sesion.token_hash == token_hash, Sesion.revocada.is_(False))
            .values(revocada=True)
        )

    def marcar_actividad(self, sesion_id: int, ahora: datetime) -> None:
        self.db.execute(
            update(Sesion).where(Sesion.id == sesion_id).values(ultima_actividad=ahora)
        )


class AuditoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def registrar(
        self,
        accion: str,
        *,
        cuenta_id: int | None = None,
        detalle: str | None = None,
        ip: str | None = None,
    ) -> None:
        """Escribe un evento sin poder romper la acción que lo originó."""
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        try:
            with self.db.begin_nested():
                self.db.add(
                    Auditoria(
                        cuenta_id=cuenta_id,
                        accion=accion,
                        detalle=detalle[:500] if detalle else None,
                        ip=ip[:64] if ip else None,
                    )
                )
        except Exception:
            logger.warning("No se pudo registrar la auditoría: %s", accion)
