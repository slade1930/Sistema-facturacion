"""Administración de categorías y productos. Rol admin; etapa C1."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor, get_db, requiere_admin, requiere_auth
from app.models.catalogo import Categoria, Producto, SectorEmpresa
from app.models.inventario import TipoMovimiento
from app.repositories.catalogo import (
    CategoriaRepository,
    IntegridadError,
    ProductoRepository,
)
from app.repositories.inventario import InventarioRepository
from app.schemas.admin import (
    CategoriaAdminRead,
    EstadoProducto,
    ProductoAdminCreate,
    ProductoAdminRead,
    ProductoAdminUpdate,
)
from app.schemas.catalogo import CategoriaCreate, CategoriaUpdate, ProductoCreate, ProductoUpdate
from app.schemas.common import Pagina
from app.services import metricas
from app.services.auth import registrar_auditoria
from app.services.inventario import ajustar

RESPUESTAS = {
    401: {"description": "API key ausente o sesión inválida."},
    403: {"description": "Se requiere una cuenta de administrador."},
}

router = APIRouter(
    prefix="/admin/catalogo",
    tags=["Administración de catálogo"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
    responses=RESPUESTAS,
)


def _conflicto(exc: IntegridadError):
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    )


def _categoria_read(db: Session, categoria: Categoria) -> CategoriaAdminRead:
    total = db.scalar(
        select(func.count(Producto.id)).where(Producto.categoria_id == categoria.id)
    ) or 0
    return CategoriaAdminRead(
        id=categoria.id,
        nombre=categoria.nombre,
        sector=categoria.sector,
        total_productos=int(total),
    )


# ---------- Categorías ----------
@router.get("/categorias", response_model=Pagina[CategoriaAdminRead])
def listar_categorias(
    sector: SectorEmpresa | None = Query(default=None),
    busqueda: str | None = Query(default=None),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return metricas.categorias_admin(
        db, sector, busqueda, desplazamiento, limite
    )


@router.get("/categorias/{categoria_id}", response_model=CategoriaAdminRead)
def obtener_categoria(categoria_id: int, db: Session = Depends(get_db)):
    categoria = CategoriaRepository(db).get(categoria_id)
    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )
    return _categoria_read(db, categoria)


@router.post(
    "/categorias",
    response_model=CategoriaAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_categoria(
    datos: CategoriaCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    repositorio = CategoriaRepository(db)
    try:
        categoria = repositorio.crear(datos, commit=False)
        registrar_auditoria(
            db,
            "categoria_creada",
            cuenta_id=actor.cuenta_id,
            detalle=f"Categoría {categoria.nombre}",
            ip=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(categoria)
    except IntegridadError as exc:
        db.rollback()
        raise _conflicto(exc) from exc
    except Exception:
        db.rollback()
        raise
    return _categoria_read(db, categoria)


@router.put("/categorias/{categoria_id}", response_model=CategoriaAdminRead)
def actualizar_categoria(
    categoria_id: int,
    datos: CategoriaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    repositorio = CategoriaRepository(db)
    categoria = repositorio.get(categoria_id)
    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )
    try:
        categoria = repositorio.actualizar(categoria, datos, commit=False)
        registrar_auditoria(
            db,
            "categoria_actualizada",
            cuenta_id=actor.cuenta_id,
            detalle=f"Categoría {categoria.nombre} (id {categoria.id})",
            ip=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(categoria)
    except IntegridadError as exc:
        db.rollback()
        raise _conflicto(exc) from exc
    except Exception:
        db.rollback()
        raise
    return _categoria_read(db, categoria)


# ---------- Productos ----------
@router.get("/productos", response_model=Pagina[ProductoAdminRead])
def listar_productos(
    categoria_id: int | None = Query(default=None, ge=1),
    sector: SectorEmpresa | None = Query(default=None),
    busqueda: str | None = Query(default=None),
    solo_activos: bool = Query(default=True),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    return metricas.catalogo_productos(
        db,
        inicio,
        fin,
        categoria_id,
        sector,
        busqueda,
        solo_activos,
        desplazamiento,
        limite,
    )


@router.get("/productos/{producto_id}", response_model=ProductoAdminRead)
def obtener_producto(
    producto_id: int,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    inicio, fin = metricas.rango(desde, hasta)
    producto = metricas.producto_admin(db, producto_id, inicio, fin)
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    return producto


@router.post(
    "/productos",
    response_model=ProductoAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_producto(
    datos: ProductoAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    datos_producto = ProductoCreate(
        **datos.model_dump(exclude={"existencias_iniciales"})
    )
    repositorio = ProductoRepository(db)
    try:
        producto = repositorio.crear(datos_producto, commit=False)
        if datos.existencias_iniciales is not None:
            inventario = InventarioRepository(db).obtener_o_crear(producto.id)
            movimiento = ajustar(
                db,
                inventario,
                existencias=datos.existencias_iniciales,
                stock_minimo=Decimal("0.00"),
                cuenta_id=actor.cuenta_id,
                motivo="Existencias iniciales al crear producto",
            )
            # El servicio de inventario registró el ajuste; la carga inicial
            # se presenta como entrada en el historial de movimientos.
            if movimiento is not None:
                movimiento.tipo = TipoMovimiento.ENTRADA
        registrar_auditoria(
            db,
            "producto_creado",
            cuenta_id=actor.cuenta_id,
            detalle=f"Producto {producto.nombre} (sku {producto.sku})",
            ip=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(producto)
    except IntegridadError as exc:
        db.rollback()
        raise _conflicto(exc) from exc
    except Exception:
        db.rollback()
        raise

    inicio, fin = metricas.rango(None, None)
    return metricas.producto_admin(db, producto.id, inicio, fin)


@router.put("/productos/{producto_id}", response_model=ProductoAdminRead)
def actualizar_producto(
    producto_id: int,
    datos: ProductoAdminUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    repositorio = ProductoRepository(db)
    producto = repositorio.get(producto_id)
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    cambios = ProductoUpdate(
        **datos.model_dump(exclude={"existencias"}, exclude_unset=True)
    )
    try:
        producto = repositorio.actualizar(producto, cambios, commit=False)
        if datos.existencias is not None:
            inventario = InventarioRepository(db).obtener_o_crear(producto.id)
            ajustar(
                db,
                inventario,
                existencias=datos.existencias,
                stock_minimo=inventario.stock_minimo,
                cuenta_id=actor.cuenta_id,
                motivo="Ajuste de existencias desde administración",
            )
        registrar_auditoria(
            db,
            "producto_actualizado",
            cuenta_id=actor.cuenta_id,
            detalle=f"Producto {producto.nombre} (id {producto.id})",
            ip=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(producto)
    except IntegridadError as exc:
        db.rollback()
        raise _conflicto(exc) from exc
    except Exception:
        db.rollback()
        raise

    inicio, fin = metricas.rango(None, None)
    return metricas.producto_admin(db, producto.id, inicio, fin)


@router.put("/productos/{producto_id}/estado", response_model=ProductoAdminRead)
def cambiar_estado_producto(
    producto_id: int,
    datos: EstadoProducto,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    repositorio = ProductoRepository(db)
    producto = repositorio.get(producto_id)
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    try:
        # Los productos con historial se conservan: solo cambian de visibilidad.
        producto.estado_activo = datos.activo
        registrar_auditoria(
            db,
            "producto_activado" if datos.activo else "producto_desactivado",
            cuenta_id=actor.cuenta_id,
            detalle=f"Producto {producto.nombre} (id {producto.id})",
            ip=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(producto)
    except Exception:
        db.rollback()
        raise

    inicio, fin = metricas.rango(None, None)
    return metricas.producto_admin(db, producto.id, inicio, fin)
