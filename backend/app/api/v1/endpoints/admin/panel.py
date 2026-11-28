"""Panel global con métricas del negocio. Rol admin; etapa C1.

Las sugerencias de ML no se calculan acá: la interfaz llama directamente a
`/api/v1/ml/pronostico` y `/api/v1/ml/anomalias/evaluar/{factura_id}`.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_db, requiere_admin, requiere_auth
from app.schemas.admin import IngresosDesglose, PanelResumen, ProductosRanking
from app.services import metricas

RESPUESTAS = {
    401: {"description": "API key ausente o sesión inválida."},
    403: {"description": "Se requiere una cuenta de administrador."},
}

router = APIRouter(
    prefix="/admin/panel",
    tags=["Administración"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
    responses=RESPUESTAS,
)


@router.get("/resumen", response_model=PanelResumen)
def panel_resumen(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db=Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.resumen(db, inicio, fin)


@router.get("/ingresos", response_model=IngresosDesglose)
def panel_ingresos(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db=Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.ingresos(db, inicio, fin)


@router.get("/productos", response_model=ProductosRanking)
def panel_productos(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db=Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.productos(db, inicio, fin)
