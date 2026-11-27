from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra todas las tablas y relaciones)
from app.db.base import Base
from app.repositories.catalogo import (
    CategoriaRepository,
    ClienteB2BRepository,
    IntegridadError,
    ProductoRepository,
)
from app.schemas.catalogo import (
    CategoriaCreate,
    ClienteB2BCreate,
    ClienteB2BUpdate,
    ProductoCreate,
    ProductoUpdate,
)


@pytest.fixture()
def db():
    """Base SQLite en memoria, nueva para cada prueba."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


def _producto(categoria_id, **extra):
    datos = dict(
        categoria_id=categoria_id,
        nombre="Galletas de chocolate",
        sku="GAL-001",
        precio_caja=Decimal("24.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=24,
    )
    datos.update(extra)
    return ProductoCreate(**datos)


# ---------------- Categoría ----------------
def test_crear_y_buscar_categoria(db):
    repo = CategoriaRepository(db)
    cat = repo.crear(CategoriaCreate(nombre="Galletas"))
    assert cat.id is not None
    assert repo.get_by_nombre("Galletas").id == cat.id


def test_categoria_duplicada_falla(db):
    repo = CategoriaRepository(db)
    repo.crear(CategoriaCreate(nombre="Galletas"))
    with pytest.raises(IntegridadError):
        repo.crear(CategoriaCreate(nombre="Galletas"))


# ---------------- Producto ----------------
def test_crear_producto_con_su_categoria(db):
    cat = CategoriaRepository(db).crear(CategoriaCreate(nombre="Galletas"))
    prod = ProductoRepository(db).crear(_producto(cat.id))
    assert prod.categoria_id == cat.id
    assert prod.precio_caja == Decimal("24.00")
    assert prod.estado_activo is True


def test_listar_filtra_por_categoria_y_busqueda(db):
    cats = CategoriaRepository(db)
    galletas = cats.crear(CategoriaCreate(nombre="Galletas"))
    bebidas = cats.crear(CategoriaCreate(nombre="Bebidas"))
    repo = ProductoRepository(db)
    repo.crear(_producto(galletas.id))
    repo.crear(_producto(bebidas.id, nombre="Jugo de naranja", sku="JUG-001"))

    assert len(repo.listar()) == 2
    assert [p.sku for p in repo.listar(categoria_id=bebidas.id)] == ["JUG-001"]
    assert [p.sku for p in repo.listar(busqueda="gal")] == ["GAL-001"]
    assert [p.sku for p in repo.listar(busqueda="JUG-0")] == ["JUG-001"]


def test_actualizar_solo_cambia_lo_enviado(db):
    cat = CategoriaRepository(db).crear(CategoriaCreate(nombre="Galletas"))
    repo = ProductoRepository(db)
    prod = repo.crear(_producto(cat.id))

    repo.actualizar(prod, ProductoUpdate(precio_unidad=Decimal("1.25")))

    assert prod.precio_unidad == Decimal("1.25")
    assert prod.nombre == "Galletas de chocolate"
    assert prod.precio_caja == Decimal("24.00")


def test_desactivar_producto_lo_oculta_del_listado(db):
    cat = CategoriaRepository(db).crear(CategoriaCreate(nombre="Galletas"))
    repo = ProductoRepository(db)
    prod = repo.crear(_producto(cat.id))

    repo.desactivar(prod)

    assert repo.listar() == []
    assert len(repo.listar(solo_activos=False)) == 1
    assert repo.get(prod.id) is not None  # no se borra


def test_sku_duplicado_falla(db):
    cat = CategoriaRepository(db).crear(CategoriaCreate(nombre="Galletas"))
    repo = ProductoRepository(db)
    repo.crear(_producto(cat.id))
    with pytest.raises(IntegridadError):
        repo.crear(_producto(cat.id, nombre="Otro producto"))


def test_producto_con_categoria_inexistente_falla(db):
    with pytest.raises(IntegridadError):
        ProductoRepository(db).crear(_producto(9999))


# ---------------- Cliente B2B ----------------
def _cliente(**extra):
    datos = dict(
        nombre_empresa="Supermercado Central",
        ruc="8-123-456",
        email_contacto="compras@central.com",
    )
    datos.update(extra)
    return ClienteB2BCreate(**datos)


def test_crear_cliente_y_buscar_por_ruc(db):
    repo = ClienteB2BRepository(db)
    cli = repo.crear(_cliente())
    assert repo.get_by_ruc("8-123-456").id == cli.id
    assert cli.activo is True


def test_ruc_duplicado_falla(db):
    repo = ClienteB2BRepository(db)
    repo.crear(_cliente())
    with pytest.raises(IntegridadError):
        repo.crear(_cliente(nombre_empresa="Otra empresa"))


def test_listar_clientes_con_busqueda_y_desactivar(db):
    repo = ClienteB2BRepository(db)
    cli = repo.crear(_cliente())
    assert len(repo.listar(busqueda="central")) == 1

    repo.actualizar(cli, ClienteB2BUpdate(telefono="507-0000"))
    assert cli.telefono == "507-0000"

    repo.desactivar(cli)
    assert repo.listar() == []


# ---------------- Esquemas (sin base de datos) ----------------
def test_precio_negativo_falla():
    with pytest.raises(ValidationError):
        _producto(1, precio_caja=Decimal("-1"))


def test_precio_con_mas_de_dos_decimales_falla():
    with pytest.raises(ValidationError):
        _producto(1, precio_unidad=Decimal("1.234"))


def test_unidades_por_caja_minimo_uno():
    with pytest.raises(ValidationError):
        _producto(1, unidades_por_caja=0)


def test_cliente_sin_ruc_falla():
    with pytest.raises(ValidationError):
        ClienteB2BCreate(nombre_empresa="X", email_contacto="a@b.com")