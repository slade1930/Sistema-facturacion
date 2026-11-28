"""Inventario global y movimientos. Rol admin; etapa A."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor, get_db, requiere_admin, requiere_auth
from app.models.catalogo import Producto
from app.repositories.inventario import InventarioRepository
from app.schemas.admin import (
    InventarioActualizar,
    InventarioRead,
    MovimientoInventarioRead,
)
from app.services.inventario import ajustar

router = APIRouter(
    prefix="/admin/inventario",
    tags=["Administración de inventario"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
)


def _leer(fila) -> InventarioRead:
    inventario, nombre, sku = fila
    return InventarioRead(
        producto_id=inventario.producto_id,
        nombre_producto=nombre,
        sku=sku,
        existencias=inventario.existencias,
        stock_minimo=inventario.stock_minimo,
        actualizado_en=inventario.actualizado_en,
    )


@router.get("", response_model=list[InventarioRead])
def listar_inventario(
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return [
        _leer(fila)
        for fila in InventarioRepository(db).listar(desplazamiento, limite)
    ]


@router.put("/{producto_id}", response_model=InventarioRead)
def actualizar_inventario(
    producto_id: int,
    datos: InventarioActualizar,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    repo = InventarioRepository(db)
    inventario = repo.obtener_o_crear(producto_id)
    try:
        ajustar(
            db,
            inventario,
            existencias=datos.existencias,
            stock_minimo=datos.stock_minimo,
            cuenta_id=actor.cuenta_id,
            motivo=datos.motivo or "Ajuste de administración",
        )
        db.commit()
        db.refresh(inventario)
    except Exception:
        db.rollback()
        raise
    producto = db.get(Producto, producto_id)
    return InventarioRead(
        producto_id=inventario.producto_id,
        nombre_producto=producto.nombre,
        sku=producto.sku,
        existencias=inventario.existencias,
        stock_minimo=inventario.stock_minimo,
        actualizado_en=inventario.actualizado_en,
    )


@router.get("/{producto_id}/movimientos", response_model=list[MovimientoInventarioRead])
def listar_movimientos(
    producto_id: int,
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return [
        MovimientoInventarioRead(
            id=movimiento.id,
            producto_id=movimiento.producto_id,
            fecha=movimiento.fecha,
            tipo=movimiento.tipo,
            cantidad=movimiento.cantidad,
            motivo=movimiento.motivo,
            factura_id=movimiento.factura_id,
            cuenta_id=movimiento.cuenta_id,
        )
        for movimiento in InventarioRepository(db).movimientos(
            producto_id, desplazamiento, limite
        )
    ]
