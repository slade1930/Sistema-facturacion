"""Consultas y bloqueo de existencias por producto. Admin y compras; etapa A."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogo import Producto
from app.models.inventario import Inventario, MovimientoInventario


class InventarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_para_actualizar(self, producto_ids: list[int]) -> list[Inventario]:
        """Bloquea las filas en orden por producto para evitar interbloqueos."""
        if not producto_ids:
            return []
        stmt = (
            select(Inventario)
            .where(Inventario.producto_id.in_(producto_ids))
            .order_by(Inventario.producto_id)
            .with_for_update()
        )
        return list(self.db.scalars(stmt).all())

    def obtener(self, producto_id: int) -> Inventario | None:
        return self.db.get(Inventario, producto_id)

    def obtener_o_crear(self, producto_id: int) -> Inventario:
        inventario = self.obtener(producto_id)
        if inventario is None:
            inventario = Inventario(
                producto_id=producto_id,
                existencias=0,
                stock_minimo=0,
            )
            self.db.add(inventario)
            self.db.flush()
        return inventario

    def listar(self, skip: int = 0, limit: int = 100):
        stmt = (
            select(Inventario, Producto.nombre, Producto.sku)
            .join(Producto, Producto.id == Inventario.producto_id)
            .order_by(Producto.nombre)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).all())

    def movimientos(
        self, producto_id: int, skip: int = 0, limit: int = 100
    ) -> list[MovimientoInventario]:
        stmt = (
            select(MovimientoInventario)
            .where(MovimientoInventario.producto_id == producto_id)
            .order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
