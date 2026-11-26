from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import get_db, requiere_auth
from app.models.catalogo import EstadoPedido, PedidoB2B
from app.repositories.pedidos import PedidoB2BRepository
from app.schemas.common import Pagina
from app.schemas.facturacion import FacturaRead
from app.schemas.pedidos import PedidoB2BRead
from app.services.pedidos import facturar_pedido_b2b

router = APIRouter(
    prefix="/pedidos",
    tags=["Facturación de pedidos"],
    dependencies=[Depends(requiere_auth)],
)


@router.get("", response_model=Pagina[PedidoB2BRead])
def listar_pedidos(
    cliente_id: int | None = None,
    estado: EstadoPedido | None = None,
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    condiciones = []
    if cliente_id is not None:
        condiciones.append(PedidoB2B.cliente_id == cliente_id)
    if estado is not None:
        condiciones.append(PedidoB2B.estado == estado)

    total = db.scalar(
        select(func.count()).select_from(PedidoB2B).where(*condiciones)
    ) or 0

    repo = PedidoB2BRepository(db)
    pedidos = repo.listar(
        cliente_id=cliente_id,
        estado=estado,
        skip=desplazamiento,
        limit=limite,
    )

    return Pagina[PedidoB2BRead](
        items=[PedidoB2BRead.model_validate(p) for p in pedidos],
        total=total,
        limite=limite,
        desplazamiento=desplazamiento,
    )


@router.get("/por-facturar", response_model=list[PedidoB2BRead])
def listar_pedidos_por_facturar(
    limite: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Pedidos pendientes o en proceso que aún no tienen factura generada."""
    stmt = (
        select(PedidoB2B)
        .options(selectinload(PedidoB2B.lineas))
        .where(
            PedidoB2B.estado.in_(
                [EstadoPedido.PENDIENTE, EstadoPedido.PROCESANDO]
            ),
            PedidoB2B.factura_generada_id.is_(None),
        )
        .order_by(PedidoB2B.id.desc())
        .limit(limite)
    )
    pedidos = db.scalars(stmt).all()
    return [PedidoB2BRead.model_validate(p) for p in pedidos]


@router.post(
    "/{pedido_id}/facturar",
    response_model=FacturaRead,
    status_code=status.HTTP_201_CREATED,
)
def facturar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    repo = PedidoB2BRepository(db)
    pedido = repo.get(pedido_id)
    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado.",
        )
    if (
        pedido.factura_generada_id is not None
        or pedido.estado == EstadoPedido.FACTURADO
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pedido ya fue facturado.",
        )
    if pedido.estado == EstadoPedido.CANCELADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un pedido cancelado no se puede facturar.",
        )

    try:
        factura = facturar_pedido_b2b(db, pedido_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(factura)
    return factura
