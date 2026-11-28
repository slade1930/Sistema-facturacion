from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor, get_db, requiere_auth
from app.models.facturacion import EstadoFactura, Factura
from app.repositories.facturacion import FacturaRepository
from app.schemas.common import Pagina
from app.schemas.facturacion import FacturaResumen

router = APIRouter(
    prefix="/historial",
    tags=["Historial"],
    dependencies=[Depends(requiere_auth)],
)


def _condiciones(
    estado: EstadoFactura | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    cliente: str | None,
    cliente_id: int | None,
):
    condiciones = []
    if cliente_id is not None:
        condiciones.append(Factura.cliente_id == cliente_id)
    if estado is not None:
        condiciones.append(Factura.estado == estado)
    if fecha_desde is not None:
        condiciones.append(Factura.fecha >= fecha_desde)
    if fecha_hasta is not None:
        condiciones.append(Factura.fecha <= fecha_hasta)
    if cliente:
        condiciones.append(Factura.cliente_nombre.ilike(f"%{cliente.strip()}%"))
    return condiciones


@router.get("", response_model=Pagina[FacturaResumen])
def listar_historial(
    estado: EstadoFactura | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    cliente: str | None = None,
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    cliente_id = actor.cliente_id if actor.es_empresa else None
    condiciones = _condiciones(
        estado, fecha_desde, fecha_hasta, cliente, cliente_id
    )
    total = db.scalar(
        select(func.count()).select_from(Factura).where(*condiciones)
    ) or 0

    facturas = FacturaRepository.listar(
        db,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        skip=desplazamiento,
        limit=limite,
        cliente_id=cliente_id,
    )

    return Pagina[FacturaResumen](
        items=[FacturaResumen.model_validate(factura) for factura in facturas],
        total=total,
        limite=limite,
        desplazamiento=desplazamiento,
    )
