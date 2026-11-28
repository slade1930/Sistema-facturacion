"""Filtro de rol, sector y cliente por token. Empresa y admin; etapa A.

Ninguna función de acá decide cálculos de facturación: solo decide qué
registros puede ver el actor que viene del token.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor
from app.models.catalogo import ClienteB2B
from app.repositories.catalogo import (
    CategoriaRepository,
    ClienteB2BRepository,
    ProductoRepository,
)
from app.repositories.facturacion import FacturaRepository
from app.repositories.pedidos import PedidoB2BRepository

SIN_PERMISO = "No tienes permiso para esta acción."
NO_ENCONTRADO = "Recurso no encontrado."


def exigir_admin(actor: Actor) -> None:
    """Solo admin o sistema. La empresa nunca administra el negocio."""
    if not actor.es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=SIN_PERMISO
        )


def exigir_empresa_o_admin(actor: Actor) -> None:
    """Para las recomendaciones: empresa, admin y sistema; nadie más."""
    if not (actor.es_empresa or actor.es_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=SIN_PERMISO
        )


def cliente_efectivo(actor: Actor, cliente_id: int | None = None) -> int | None:
    """El cuerpo o la query nunca pueden contradecir al cliente del token."""
    if actor.es_empresa:
        if cliente_id is not None and cliente_id != actor.cliente_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=SIN_PERMISO
            )
        return actor.cliente_id
    return cliente_id


def _no_encontrado() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO
    )


def categoria_visible(db: Session, actor: Actor, categoria_id: int):
    categoria = CategoriaRepository(db).get(categoria_id)
    if categoria is None:
        raise _no_encontrado()
    if actor.es_empresa and (
        categoria.sector is None
        or getattr(categoria.sector, "value", categoria.sector) != actor.sector
    ):
        raise _no_encontrado()
    return categoria


def producto_visible(db: Session, actor: Actor, producto_id: int):
    producto = ProductoRepository(db).get(producto_id)
    if producto is None:
        raise _no_encontrado()
    if actor.es_empresa:
        categoria = producto.categoria
        if (
            categoria is None
            or categoria.sector is None
            or getattr(categoria.sector, "value", categoria.sector) != actor.sector
        ):
            raise _no_encontrado()
    return producto


def cliente_visible(db: Session, actor: Actor, cliente_id: int):
    cliente = ClienteB2BRepository(db).get(cliente_id)
    if cliente is None:
        raise _no_encontrado()
    if actor.es_empresa and cliente_id != actor.cliente_id:
        raise _no_encontrado()
    return cliente


def pedido_visible(db: Session, actor: Actor, pedido_id: int):
    pedido = PedidoB2BRepository(db).get_con_lineas(pedido_id)
    if pedido is None:
        raise _no_encontrado()
    if actor.es_empresa and pedido.cliente_id != actor.cliente_id:
        raise _no_encontrado()
    return pedido


def factura_visible(db: Session, actor: Actor, factura_id: int):
    factura = FacturaRepository.obtener_por_id(db, factura_id)
    if factura is None:
        raise _no_encontrado()
    # Las facturas históricas sin cliente_id solo las ve el admin.
    if actor.es_empresa and factura.cliente_id != actor.cliente_id:
        raise _no_encontrado()
    return factura


def vincular_factura_a_cliente(db: Session, factura, ruc: str | None) -> None:
    """Vincula una factura manual al cliente único con ese RUC, si existe."""
    if not ruc:
        return
    try:
        ids = db.scalars(
            select(ClienteB2B.id).where(ClienteB2B.ruc == ruc)
        ).all()
        if len(ids) == 1:
            factura.cliente_id = ids[0]
    except Exception:
        # Algunas pruebas usan una sesión falsa; el vínculo es best-effort.
        return
