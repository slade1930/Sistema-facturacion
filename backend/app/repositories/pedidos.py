"""Acceso a datos SQLAlchemy para pedidos B2B y líneas de pedido."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.catalogo import LineaPedidoB2B, PedidoB2B
from app.schemas.pedidos import (
    LineaPedidoB2BCreate,
    LineaPedidoB2BUpdate,
    PedidoB2BCreate,
    PedidoB2BUpdate,
)


class IntegridadPedidoError(Exception):
    """Referencia inexistente o restricción de integridad incumplida."""


def _guardar(db: Session, obj, commit: bool):
    """Persiste el objeto; con commit=False solo ejecuta flush."""
    try:
        db.add(obj)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise IntegridadPedidoError(
            "No se pudo guardar el pedido: revise las referencias y restricciones."
        ) from exc
    return obj


class PedidoB2BRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, pedido_id: int) -> PedidoB2B | None:
        return self.db.get(PedidoB2B, pedido_id)

    def get_con_lineas(self, pedido_id: int) -> PedidoB2B | None:
        stmt = (
            select(PedidoB2B)
            .options(selectinload(PedidoB2B.lineas))
            .where(PedidoB2B.id == pedido_id)
        )
        return self.db.scalar(stmt)

    def listar(
        self,
        cliente_id: int | None = None,
        estado=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PedidoB2B]:
        stmt = select(PedidoB2B).options(selectinload(PedidoB2B.lineas))
        if cliente_id is not None:
            stmt = stmt.where(PedidoB2B.cliente_id == cliente_id)
        if estado is not None:
            stmt = stmt.where(PedidoB2B.estado == estado)
        return list(
            self.db.scalars(
                stmt.order_by(PedidoB2B.id.desc()).offset(skip).limit(limit)
            ).all()
        )

    def crear(self, datos: PedidoB2BCreate, commit: bool = False) -> PedidoB2B:
        payload = datos.model_dump(exclude={"lineas"})
        pedido = PedidoB2B(**payload)
        for idx, linea_data in enumerate(datos.lineas, start=1):
            linea_dict = linea_data.model_dump()
            if "orden" not in linea_data.model_fields_set:
                linea_dict["orden"] = idx
            pedido.lineas.append(LineaPedidoB2B(**linea_dict))
        return _guardar(self.db, pedido, commit)

    def actualizar(
        self, obj: PedidoB2B, datos: PedidoB2BUpdate, commit: bool = False
    ) -> PedidoB2B:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(obj, campo, valor)
        return _guardar(self.db, obj, commit)


class LineaPedidoB2BRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, linea_id: int) -> LineaPedidoB2B | None:
        return self.db.get(LineaPedidoB2B, linea_id)

    def listar_por_pedido(self, pedido_id: int) -> list[LineaPedidoB2B]:
        stmt = (
            select(LineaPedidoB2B)
            .where(LineaPedidoB2B.pedido_id == pedido_id)
            .order_by(LineaPedidoB2B.orden, LineaPedidoB2B.id)
        )
        return list(self.db.scalars(stmt).all())

    def crear(
        self,
        pedido_id: int,
        datos: LineaPedidoB2BCreate,
        commit: bool = False,
    ) -> LineaPedidoB2B:
        valores = datos.model_dump()
        linea = LineaPedidoB2B(pedido_id=pedido_id, **valores)
        return _guardar(self.db, linea, commit)

    def actualizar(
        self,
        obj: LineaPedidoB2B,
        datos: LineaPedidoB2BUpdate,
        commit: bool = False,
    ) -> LineaPedidoB2B:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(obj, campo, valor)
        return _guardar(self.db, obj, commit)

    def eliminar(self, obj: LineaPedidoB2B, commit: bool = False) -> None:
        try:
            self.db.delete(obj)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise IntegridadPedidoError(
                "No se pudo eliminar la línea del pedido."
            ) from exc
