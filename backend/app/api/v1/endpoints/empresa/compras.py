"""Compra con pedido, factura automática e inventario. Rol empresa; etapa A."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_db, requiere_auth, requiere_empresa
from app.models.catalogo import EstadoPedido, LineaPedidoB2B, PedidoB2B, TipoEmpaque
from app.repositories.facturacion import FacturaRepository
from app.repositories.inventario import InventarioRepository
from app.schemas.compras import CompraCreate, CompraResponse
from app.services.aislamiento import producto_visible
from app.services.inventario import descontar, unidades_a_descontar
from app.services.pedidos import (
    LineaPedido,
    calcular_pedido,
    facturar_pedido_b2b,
    precio_de_presentacion,
)

router = APIRouter(
    prefix="/compras",
    tags=["Compras del portal"],
    dependencies=[Depends(requiere_auth)],
)


def _respuesta(factura, pedido_id: int, reutilizada: bool = False) -> CompraResponse:
    return CompraResponse(
        pedido_id=pedido_id,
        factura_id=factura.id,
        numero_serie=factura.numero_serie,
        total=factura.total,
        pdf_url=f"/api/v1/facturas/{factura.id}/pdf",
        reutilizada=reutilizada,
    )


def _pedido_por_clave(db: Session, cliente_id: int, clave: str | None):
    if not clave:
        return None
    return db.scalar(
        select(PedidoB2B).where(
            PedidoB2B.cliente_id == cliente_id,
            PedidoB2B.clave_idempotencia == clave,
        )
    )


def _reutilizar(db: Session, pedido: PedidoB2B) -> CompraResponse:
    if pedido.factura_generada_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una compra en curso con esa clave. Inténtalo de nuevo.",
        )
    factura = FacturaRepository.obtener_por_id(db, pedido.factura_generada_id)
    if factura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada.",
        )
    return _respuesta(factura, pedido.id, reutilizada=True)


@router.post("", response_model=CompraResponse, status_code=status.HTTP_201_CREATED)
def comprar(
    datos: CompraCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(requiere_empresa),
):
    """Confirma la compra en una sola transacción: pedido, factura y stock."""
    anterior = _pedido_por_clave(db, actor.cliente_id, datos.clave_idempotencia)
    if anterior is not None:
        return _reutilizar(db, anterior)

    lineas = []
    for item in datos.lineas:
        producto = producto_visible(db, actor, item.producto_id)
        if not producto.estado_activo:
            raise HTTPException(
                status_code=422,
                detail=f"El producto '{producto.nombre}' no está activo.",
            )
        try:
            precio = precio_de_presentacion(producto, item.tipo_empaque)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        lineas.append(
            LineaPedido(
                descripcion=producto.nombre,
                presentacion=item.tipo_empaque,
                cantidad=item.cantidad,
                precio=precio,
                unidades_por_caja=producto.unidades_por_caja,
                precio_unidad=(
                    producto.precio_unidad
                    if item.tipo_empaque == TipoEmpaque.UNIDAD
                    else None
                ),
                gravada=producto.aplica_itbms,
                descuento_pct=Decimal(
                    str(getattr(producto, "descuento_pct", 0) or 0)
                ),
                producto_id=producto.id,
            )
        )

    try:
        resumen = calcular_pedido(lineas)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    requerido: dict[int, Decimal] = {}
    for linea in lineas:
        cantidad = unidades_a_descontar(
            linea.presentacion, linea.cantidad, linea.unidades_por_caja
        )
        requerido[linea.producto_id] = (
            requerido.get(linea.producto_id, Decimal(0)) + cantidad
        )

    inventarios = {
        inv.producto_id: inv
        for inv in InventarioRepository(db).listar_para_actualizar(sorted(requerido))
    }
    for producto_id, cantidad in requerido.items():
        inventario = inventarios.get(producto_id)
        if inventario is not None and inventario.existencias < cantidad:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente para el producto {producto_id}.",
            )

    pedido = PedidoB2B(
        cliente_id=actor.cliente_id,
        estado=EstadoPedido.PENDIENTE,
        total_estimado=resumen.subtotal,
        notas=datos.notas,
        clave_idempotencia=datos.clave_idempotencia,
    )
    for orden, linea in enumerate(lineas, start=1):
        pedido.lineas.append(
            LineaPedidoB2B(
                producto_id=linea.producto_id,
                tipo_empaque=linea.presentacion,
                cantidad=linea.cantidad,
                subtotal=linea.subtotal,
                orden=orden,
            )
        )
    db.add(pedido)

    try:
        db.flush()
        factura = facturar_pedido_b2b(db, pedido.id)
        descontar(
            db,
            inventarios,
            requerido,
            factura_id=factura.id,
            cuenta_id=actor.cuenta_id,
            numero_serie=factura.numero_serie,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        repetido = _pedido_por_clave(db, actor.cliente_id, datos.clave_idempotencia)
        if repetido is not None and repetido.factura_generada_id is not None:
            return _reutilizar(db, repetido)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo confirmar la compra. Inténtalo de nuevo.",
        ) from None
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    db.refresh(factura)
    return _respuesta(factura, pedido.id)
