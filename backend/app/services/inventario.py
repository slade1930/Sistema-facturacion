"""Descuento, ajuste y movimientos de existencias. Admin y compras; etapa A."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import TipoEmpaque
from app.models.facturacion import EstadoFactura, Factura
from app.models.inventario import Inventario, MovimientoInventario, TipoMovimiento
from app.repositories.inventario import InventarioRepository

PREFIJO_DEVOLUCION = "anulación de la factura "


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


def devolver_por_factura(
    db: Session, factura_id: int, cuenta_id: int | None
) -> int:
    """Repone el stock de una factura ya anulada y devuelve cuántos productos repuso.

    Solo repone productos que tienen fila de inventario y una salida ligada a la
    factura. No hace commit: la transacción que anuló la factura debe cerrarla.
    Es idempotente: si ya existen entradas de anulación para la factura, no
    vuelve a reponer. Una factura sin movimientos no produce cambios.

    La duplicación de facturas no descuenta stock: el endpoint ``/duplicar`` solo
    copia la factura y sus líneas, sin crear movimientos de inventario. Por eso
    tampoco hay devolución al anular una factura duplicada sin salidas propias.
    """
    factura = db.get(Factura, factura_id)
    if factura is None or factura.estado != EstadoFactura.ANULADA:
        return 0

    repositorio = InventarioRepository(db)
    if repositorio.ya_devolvio_factura(factura_id):
        return 0

    salidas = repositorio.salidas_por_factura(factura_id)
    if not salidas:
        return 0

    producto_ids = [producto_id for producto_id, _ in salidas]
    inventarios = {
        inventario.producto_id: inventario
        for inventario in repositorio.listar_para_actualizar(producto_ids)
    }
    # La segunda comprobación ocurre bajo los bloqueos de inventario: dos
    # anulaciones concurrentes no pueden reponer dos veces la misma salida.
    if repositorio.ya_devolvio_factura(factura_id):
        return 0

    ahora = datetime.now(timezone.utc)
    motivo = f"{PREFIJO_DEVOLUCION}{factura.numero_serie}"[:200]
    repuestos = 0
    for producto_id, cantidad in salidas:
        inventario = inventarios.get(producto_id)
        if inventario is None:
            # Defensivo: la consulta ya exige fila de inventario.
            continue
        inventario.existencias += cantidad
        inventario.actualizado_en = ahora
        db.add(
            MovimientoInventario(
                producto_id=producto_id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=cantidad,
                motivo=motivo,
                factura_id=factura_id,
                cuenta_id=cuenta_id,
            )
        )
        repuestos += 1
    return repuestos
