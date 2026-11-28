"""Sesión actual, cierre y cambio de clave. Empresa y admin; etapa A."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor
from app.db.session import get_db
from app.repositories.cuentas import CuentasRepository
from app.schemas.auth import CambiarClaveEntrada, MensajeSalida, YoSalida
from app.schemas.empresa import resumen_empresa
from app.services.auth import (
    cambiar_clave,
    cerrar_sesion,
    registrar_auditoria,
    verificar_clave,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _cuenta_actual(db: Session, actor: Actor):
    if actor.cuenta_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se necesita una sesión.",
        )
    cuenta = CuentasRepository(db).por_id(actor.cuenta_id)
    if cuenta is None or not cuenta.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada.",
        )
    return cuenta


@router.get("/yo", response_model=YoSalida)
def ver_yo(db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    cuenta = _cuenta_actual(db, actor)
    return YoSalida(
        rol=cuenta.rol.value,
        cuenta_id=cuenta.id,
        empresa=resumen_empresa(cuenta.cliente) if cuenta.cliente else None,
        debe_cambiar_clave=cuenta.debe_cambiar_clave,
    )


@router.post("/logout", response_model=MensajeSalida)
def cerrar_sesion_actual(
    db: Session = Depends(get_db), actor: Actor = Depends(get_actor)
):
    _cuenta_actual(db, actor)
    cerrar_sesion(db, actor.token)
    registrar_auditoria(db, "logout", cuenta_id=actor.cuenta_id)
    db.commit()
    return MensajeSalida(detalle="Sesión cerrada.")


@router.post("/cambiar-clave", response_model=MensajeSalida)
def cambiar_contrasena(
    datos: CambiarClaveEntrada,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    cuenta = _cuenta_actual(db, actor)
    if not verificar_clave(datos.contrasena_actual, cuenta.password_hash):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña actual no es correcta.",
        )
    cambiar_clave(db, cuenta, datos.contrasena_nueva, token_actual=actor.token)
    registrar_auditoria(db, "cambio_clave", cuenta_id=cuenta.id)
    db.commit()
    return MensajeSalida(detalle="Contraseña actualizada.")
