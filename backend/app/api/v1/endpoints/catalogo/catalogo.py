
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.deps import requiere_auth
from app.db.session import get_db
from app.repositories.catalogo import (
    CategoriaRepository,
    ClienteB2BRepository,
    IntegridadError,
    ProductoRepository,
)
from app.schemas.catalogo import (
    CategoriaCreate,
    CategoriaRead,
    CategoriaUpdate,
    ClienteB2BCreate,
    ClienteB2BRead,
    ClienteB2BUpdate,
    ProductoCreate,
    ProductoRead,
    ProductoUpdate,
)

router = APIRouter(
    prefix="",
    tags=["Catálogo"],
    dependencies=[Depends(requiere_auth)],
)


# =========================
# CATEGORÍAS
# =========================

@router.get("/categorias", response_model=list[CategoriaRead])
def listar_categorias(
    busqueda: str | None = Query(default=None),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return CategoriaRepository(db).listar(busqueda, desplazamiento, limite)


@router.get("/categorias/{categoria_id}", response_model=CategoriaRead)
def obtener_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
):
    categoria = CategoriaRepository(db).get(categoria_id)

    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )

    return categoria


@router.post(
    "/categorias",
    response_model=CategoriaRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_categoria(
    datos: CategoriaCreate,
    db: Session = Depends(get_db),
):
    repositorio = CategoriaRepository(db)

    try:
        categoria = repositorio.crear(datos, commit=False)
        db.commit()
        db.refresh(categoria)
        return categoria
    except IntegridadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put("/categorias/{categoria_id}", response_model=CategoriaRead)
def actualizar_categoria(
    categoria_id: int,
    datos: CategoriaUpdate,
    db: Session = Depends(get_db),
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
        db.commit()
        db.refresh(categoria)
        return categoria
    except IntegridadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# =========================
# PRODUCTOS
# =========================

@router.get("/productos", response_model=list[ProductoRead])
def listar_productos(
    categoria_id: int | None = Query(default=None, ge=1),
    busqueda: str | None = Query(default=None),
    solo_activos: bool = Query(default=True),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ProductoRepository(db).listar(
        categoria_id=categoria_id,
        busqueda=busqueda,
        solo_activos=solo_activos,
        skip=desplazamiento,
        limit=limite,
    )


@router.get("/productos/{producto_id}", response_model=ProductoRead)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto = ProductoRepository(db).get(producto_id)

    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    return producto


@router.post(
    "/productos",
    response_model=ProductoRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_producto(
    datos: ProductoCreate,
    db: Session = Depends(get_db),
):
    repositorio = ProductoRepository(db)

    try:
        producto = repositorio.crear(datos, commit=False)
        db.commit()
        db.refresh(producto)
        return producto
    except IntegridadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put("/productos/{producto_id}", response_model=ProductoRead)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate,
    db: Session = Depends(get_db),
):
    repositorio = ProductoRepository(db)
    producto = repositorio.get(producto_id)

    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    try:
        producto = repositorio.actualizar(producto, datos, commit=False)
        db.commit()
        db.refresh(producto)
        return producto
    except IntegridadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete("/productos/{producto_id}", response_model=ProductoRead)
def desactivar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    repositorio = ProductoRepository(db)
    producto = repositorio.get(producto_id)

    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    producto = repositorio.desactivar(producto, commit=False)
    db.commit()
    db.refresh(producto)

    return producto


# =========================
# CLIENTES B2B
# =========================

@router.get("/clientes", response_model=list[ClienteB2BRead])
def listar_clientes(
    busqueda: str | None = Query(default=None),
    solo_activos: bool = Query(default=True),
    desplazamiento: int = Query(default=0, ge=0),
    limite: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ClienteB2BRepository(db).listar(
        busqueda=busqueda,
        solo_activos=solo_activos,
        skip=desplazamiento,
        limit=limite,
    )


@router.get("/clientes/{cliente_id}", response_model=ClienteB2BRead)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    cliente = ClienteB2BRepository(db).get(cliente_id)

    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )

    return cliente


@router.post(
    "/clientes",
    response_model=ClienteB2BRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_cliente(
    datos: ClienteB2BCreate,
    db: Session = Depends(get_db),
):
    repositorio = ClienteB2BRepository(db)

    try:
        cliente = repositorio.crear(datos, commit=False)
        db.commit()
        db.refresh(cliente)
        return cliente
    except IntegridadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put("/clientes/{cliente_id}", response_model=ClienteB2BRead)
def actualizar_cliente(
    cliente_id: int,
    datos: ClienteB2BUpdate,
    db: Session = Depends(get_db),
):
    repositorio = ClienteB2BRepository(db)
    cliente = repositorio.get(cliente_id)

    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )

    try:
        cliente = repositorio.actualizar(cliente, datos, commit=False)
        db.commit()
        db.refresh(cliente)
        return cliente
    except IntegridadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete("/clientes/{cliente_id}", response_model=ClienteB2BRead)
def desactivar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    repositorio = ClienteB2BRepository(db)
    cliente = repositorio.get(cliente_id)

    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )

    cliente = repositorio.desactivar(cliente, commit=False)
    db.commit()
    db.refresh(cliente)

    return cliente
