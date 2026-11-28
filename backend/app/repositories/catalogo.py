from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, ClienteB2B, Producto
from app.schemas.catalogo import (
    CategoriaCreate,
    CategoriaUpdate,
    ClienteB2BCreate,
    ClienteB2BUpdate,
    ProductoCreate,
    ProductoUpdate,
)


class IntegridadError(Exception):
    """Valor único repetido (sku, ruc, nombre de categoría) o referencia inexistente."""


def _guardar(db: Session, obj, commit: bool):
    """Guarda el objeto. Con commit=False solo hace flush (lo confirma quien llama)."""
    try:
        db.add(obj)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise IntegridadError(
            "Valor duplicado o referencia inexistente (sku, ruc, nombre o categoria_id)."
        ) from exc
    return obj


class CategoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, categoria_id: int) -> Categoria | None:
        return self.db.get(Categoria, categoria_id)

    def get_by_nombre(self, nombre: str) -> Categoria | None:
        return self.db.scalar(select(Categoria).where(Categoria.nombre == nombre))

    def listar(
        self,
        busqueda: str | None = None,
        skip: int = 0,
        limit: int = 100,
        sector: str | None = None,
    ):
        stmt = select(Categoria)
        if busqueda:
            stmt = stmt.where(Categoria.nombre.ilike(f"%{busqueda}%"))
        if sector is not None:
            stmt = stmt.where(Categoria.sector == sector)
        return self.db.scalars(
            stmt.order_by(Categoria.nombre).offset(skip).limit(limit)
        ).all()

    def crear(self, datos: CategoriaCreate, commit: bool = True) -> Categoria:
        return _guardar(self.db, Categoria(**datos.model_dump()), commit)

    def actualizar(
        self, obj: Categoria, datos: CategoriaUpdate, commit: bool = True
    ) -> Categoria:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(obj, campo, valor)
        return _guardar(self.db, obj, commit)

    def eliminar(self, obj: Categoria, commit: bool = True) -> None:
        try:
            self.db.delete(obj)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise IntegridadError(
                "No se puede eliminar la categoría porque tiene productos asociados."
            ) from exc


class ProductoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, producto_id: int) -> Producto | None:
        return self.db.get(Producto, producto_id)

    def get_by_sku(self, sku: str) -> Producto | None:
        return self.db.scalar(select(Producto).where(Producto.sku == sku))

    def listar(
        self,
        categoria_id: int | None = None,
        busqueda: str | None = None,
        solo_activos: bool = True,
        skip: int = 0,
        limit: int = 100,
        sector: str | None = None,
    ):
        stmt = select(Producto)
        if sector is not None:
            stmt = stmt.join(Producto.categoria).where(Categoria.sector == sector)
        if solo_activos:
            stmt = stmt.where(Producto.estado_activo.is_(True))
        if categoria_id is not None:
            stmt = stmt.where(Producto.categoria_id == categoria_id)
        if busqueda:
            patron = f"%{busqueda}%"
            stmt = stmt.where(
                or_(Producto.nombre.ilike(patron), Producto.sku.ilike(patron))
            )
        return self.db.scalars(
            stmt.order_by(Producto.nombre).offset(skip).limit(limit)
        ).all()

    def crear(self, datos: ProductoCreate, commit: bool = True) -> Producto:
        return _guardar(self.db, Producto(**datos.model_dump()), commit)

    def actualizar(
        self, obj: Producto, datos: ProductoUpdate, commit: bool = True
    ) -> Producto:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(obj, campo, valor)
        return _guardar(self.db, obj, commit)

    def desactivar(self, obj: Producto, commit: bool = True) -> Producto:
        obj.estado_activo = False
        return _guardar(self.db, obj, commit)


class ClienteB2BRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, cliente_id: int) -> ClienteB2B | None:
        return self.db.get(ClienteB2B, cliente_id)

    def get_by_ruc(self, ruc: str) -> ClienteB2B | None:
        return self.db.scalar(select(ClienteB2B).where(ClienteB2B.ruc == ruc))

    def listar(
        self,
        busqueda: str | None = None,
        solo_activos: bool = True,
        skip: int = 0,
        limit: int = 100,
        cliente_id: int | None = None,
    ):
        stmt = select(ClienteB2B)
        if cliente_id is not None:
            stmt = stmt.where(ClienteB2B.id == cliente_id)
        if solo_activos:
            stmt = stmt.where(ClienteB2B.activo.is_(True))
        if busqueda:
            patron = f"%{busqueda}%"
            stmt = stmt.where(
                or_(
                    ClienteB2B.nombre_empresa.ilike(patron),
                    ClienteB2B.ruc.ilike(patron),
                )
            )
        return self.db.scalars(
            stmt.order_by(ClienteB2B.nombre_empresa).offset(skip).limit(limit)
        ).all()

    def crear(self, datos: ClienteB2BCreate, commit: bool = True) -> ClienteB2B:
        return _guardar(self.db, ClienteB2B(**datos.model_dump()), commit)

    def actualizar(
        self, obj: ClienteB2B, datos: ClienteB2BUpdate, commit: bool = True
    ) -> ClienteB2B:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(obj, campo, valor)
        return _guardar(self.db, obj, commit)

    def desactivar(self, obj: ClienteB2B, commit: bool = True) -> ClienteB2B:
        obj.activo = False
        return _guardar(self.db, obj, commit)
