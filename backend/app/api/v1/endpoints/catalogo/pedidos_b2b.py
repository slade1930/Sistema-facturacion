from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_auth
from app.models.catalogo import EstadoPedido, PedidoB2B
from app.repositories.pedidos import IntegridadPedidoError, PedidoB2BRepository
from app.schemas.common import Pagina
from app.schemas.pedidos import PedidoB2BCreate, PedidoB2BRead

router = APIRouter(
    prefix="/pedidos-b2b",
    tags=["Pedidos B2B"],
    dependencies=[Depends(requiere_auth)],
)


def _condiciones(
    cliente_id: int | None,
    estado: EstadoPedido | None,
):
    condiciones = []
    if cliente_id is not None:
        condiciones.append(PedidoB2B.cliente_id == cliente_id)
    if estado is not None:
        condiciones.append(PedidoB2B.estado == estado)
    return condiciones


@router.post(
    "",
    response_model=PedidoB2BRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido(datos: PedidoB2BCreate, db: Session = Depends(get_db)):
    repo = PedidoB2BRepository(db)
    try:
        pedido = repo.crear(datos, commit=False)
    except IntegridadPedidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    db.commit()
    db.refresh(pedido)
    return pedido


@router.get("", response_model=Pagina[PedidoB2BRead])
def listar_pedidos(
    cliente_id: int | None = None,
    estado: EstadoPedido | None = None,
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    condiciones = _condiciones(cliente_id, estado)
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


@router.get("/{pedido_id}", response_model=PedidoB2BRead)
def obtener_pedido(pedido_id: int, db: Session = Depends(get_db)):
    repo = PedidoB2BRepository(db)
    pedido = repo.get_con_lineas(pedido_id)
    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado.",
        )
    return pedido
