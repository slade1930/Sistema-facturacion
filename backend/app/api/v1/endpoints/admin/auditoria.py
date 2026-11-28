"""Consulta de eventos de auditoría. Rol admin; etapa C1."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_db, requiere_admin, requiere_auth
from app.schemas.admin import AuditoriaRead
from app.schemas.common import Pagina
from app.services import metricas

RESPUESTAS = {
    401: {"description": "API key ausente o sesión inválida."},
    403: {"description": "Se requiere una cuenta de administrador."},
}

router = APIRouter(
    prefix="/admin/auditoria",
    tags=["Administración"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
    responses=RESPUESTAS,
)


@router.get("", response_model=Pagina[AuditoriaRead])
def listar_auditoria(
    accion: str | None = Query(default=None),
    cuenta_id: int | None = Query(default=None, ge=1),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.listar_auditoria(
        db, accion, cuenta_id, inicio, fin, desplazamiento, limite
    )
