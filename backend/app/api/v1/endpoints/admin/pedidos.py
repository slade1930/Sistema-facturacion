"""Consulta global de pedidos. Rol admin; etapa C1."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.deps import get_db, requiere_admin, requiere_auth
from app.api.v1.endpoints.facturacion.pedidos import listar_pedidos_por_facturar
from app.repositories.pedidos import PedidoB2BRepository
from app.schemas.admin import PedidoAdminRead
from app.schemas.common import Pagina
from app.schemas.pedidos import PedidoB2BRead
from app.services import metricas
from app.models.catalogo import EstadoPedido

RESPUESTAS = {
    401: {"description": "API key ausente o sesión inválida."},
    403: {"description": "Se requiere una cuenta de administrador."},
}

router = APIRouter(
    prefix="/admin/pedidos",
    tags=["Administración de pedidos"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
    responses=RESPUESTAS,
)


@router.get("", response_model=Pagina[PedidoAdminRead])
def listar_pedidos_admin(
    estado: EstadoPedido | None = Query(default=None),
    empresa_id: int | None = Query(default=None, ge=1),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.listar_pedidos(
        db, inicio, fin, estado, empresa_id, desplazamiento, limite
    )


# Antes de /{pedido_id}; se reutiliza la lógica del endpoint existente.
@router.get("/por-facturar", response_model=list[PedidoB2BRead])
def listar_por_facturar_admin(
    limite: int = Query(default=100, ge=1, le=500),
    db=Depends(get_db),
):
    return listar_pedidos_por_facturar(db=db, limite=limite)


@router.get("/{pedido_id}", response_model=PedidoAdminRead)
def obtener_pedido_admin(pedido_id: int, db=Depends(get_db)):
    pedido = PedidoB2BRepository(db).get_con_lineas(pedido_id)
    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado.",
        )
    datos = PedidoB2BRead.model_validate(pedido).model_dump()
    return PedidoAdminRead(
        **datos,
        nombre_empresa=pedido.cliente.nombre_empresa if pedido.cliente else None,
    )
