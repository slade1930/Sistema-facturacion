"""Descuento, ajuste y movimientos de existencias. Admin y compras; etapa A."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import TipoEmpaque
from app.models.inventario import Inventario, MovimientoInventario, TipoMovimiento


def unidades_a_descontar(
    presentacion: TipoEmpaque,
    cantidad: Decimal,
    unidades_por_caja: int,
) -> Decimal:
    """Convierte la presentación comprada a unidades base, sin redondear."""
    unidades = Decimal(cantidad)
    por_caja = Decimal(unidades_por_caja)
    if presentacion == TipoEmpaque.CAJA:
        return unidades * por_caja
    if presentacion == TipoEmpaque.MEDIA_CAJA:
        return unidades * por_caja / Decimal(2)
    if presentacion == TipoEmpaque.UNIDAD:
        return unidades
    raise ValueError(f"Presentación no soportada: {presentacion}")


def descontar(
    db: Session,
    inventarios: dict[int, Inventario],
    requerido: dict[int, Decimal],
    *,
    factura_id: int,
    cuenta_id: int | None,
    numero_serie: str,
) -> None:
    """Descuenta existencias y deja un movimiento de salida por factura."""
    ahora = datetime.now(timezone.utc)
    for producto_id, cantidad in sorted(requerido.items()):
        inventario = inventarios.get(producto_id)
        if inventario is None:
            # Sin fila de inventario no hay control de stock.
            continue
        inventario.existencias -= cantidad
        inventario.actualizado_en = ahora
        db.add(
            MovimientoInventario(
                producto_id=producto_id,
                tipo=TipoMovimiento.SALIDA,
                cantidad=cantidad,
                motivo=f"Compra del portal - factura {numero_serie}"[:200],
                factura_id=factura_id,
                cuenta_id=cuenta_id,
            )
        )


def ajustar(
    db: Session,
    inventario: Inventario,
    *,
    existencias: Decimal,
    stock_minimo: Decimal,
    cuenta_id: int | None,
    motivo: str,
) -> MovimientoInventario | None:
    """Aplica un ajuste de admin y registra el movimiento si hay cambio."""
    anterior = inventario.existencias
    inventario.existencias = existencias
    inventario.stock_minimo = stock_minimo
    inventario.actualizado_en = datetime.now(timezone.utc)
    diferencia = abs(existencias - anterior)
    if diferencia == 0:
        return None
    movimiento = MovimientoInventario(
        producto_id=inventario.producto_id,
        tipo=TipoMovimiento.AJUSTE,
        cantidad=diferencia,
        motivo=motivo[:200],
        cuenta_id=cuenta_id,
    )
    db.add(movimiento)
    return movimiento
