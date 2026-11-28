"""Alta, consulta y suspensión de empresas. Rol admin; etapa C1."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor, get_db, requiere_admin, requiere_auth
from app.models.catalogo import ClienteB2B, SectorEmpresa
from app.models.seguridad import Cuenta, RolCuenta
from app.schemas.admin import EmpresaDetalle, EmpresaResumen, EstadoEmpresa
from app.schemas.common import Pagina
from app.services import metricas
from app.services.auth import (
    activar_cuenta,
    desactivar_cuenta,
    registrar_auditoria,
)

RESPUESTAS = {
    401: {"description": "API key ausente o sesión inválida."},
    403: {"description": "Se requiere una cuenta de administrador."},
}

router = APIRouter(
    prefix="/admin/empresas",
    tags=["Administración de empresas"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
    responses=RESPUESTAS,
)


@router.get("", response_model=Pagina[EmpresaResumen])
def listar_empresas(
    sector: SectorEmpresa | None = Query(default=None),
    activo: bool | None = Query(default=None),
    busqueda: str | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.listar_empresas(
        db, inicio, fin, sector, activo, busqueda, desplazamiento, limite
    )


@router.get("/{empresa_id}", response_model=EmpresaDetalle)
def obtener_empresa(
    empresa_id: int,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    detalle = metricas.detalle_empresa(db, empresa_id, inicio, fin)
    if detalle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada.",
        )
    return detalle


@router.put("/{empresa_id}/estado", response_model=EmpresaResumen)
def cambiar_estado_empresa(
    empresa_id: int,
    datos: EstadoEmpresa,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    cliente = db.get(ClienteB2B, empresa_id)
    cuenta = db.scalar(
        select(Cuenta).where(
            Cuenta.cliente_id == empresa_id,
            Cuenta.rol == RolCuenta.EMPRESA,
        )
    )
    if cliente is None or cuenta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada.",
        )

    try:
        cliente.activo = datos.activo
        if datos.activo:
            activar_cuenta(db, cuenta)
            accion = "empresa_activada"
        else:
            desactivar_cuenta(db, cuenta)
            accion = "empresa_suspendida"
        registrar_auditoria(
            db,
            accion,
            cuenta_id=actor.cuenta_id,
            detalle=(
                f"Empresa {cliente.nombre_empresa} (id {cliente.id})"
                + (f": {datos.motivo}" if datos.motivo else "")
            )[:500],
            ip=request.client.host if request.client else None,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    detalle = metricas.detalle_empresa(
        db, empresa_id, *metricas.rango(None, None)
    )
    return detalle
