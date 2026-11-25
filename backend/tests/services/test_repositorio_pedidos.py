from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.models.catalogo import EstadoPedido, TipoEmpaque
from app.repositories.catalogo import (
    CategoriaRepository,
    ClienteB2BRepository,
    ProductoRepository,
)
from app.repositories.pedidos import (
    IntegridadPedidoError,
    LineaPedidoB2BRepository,
    PedidoB2BRepository,
)
from app.schemas.catalogo import CategoriaCreate, ClienteB2BCreate, ProductoCreate
from app.schemas.pedidos import (
    LineaPedidoB2BCreate,
    LineaPedidoB2BUpdate,
    PedidoB2BCreate,
    PedidoB2BUpdate,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _cliente(db):
    return ClienteB2BRepository(db).crear(
        ClienteB2BCreate(
            nombre_empresa="Comercial de Prueba",
            ruc="8-999-111",
            email_contacto="compras@prueba.com",
        ),
        commit=True,
    )


def _producto(db):
    categoria = CategoriaRepository(db).crear(
        CategoriaCreate(nombre="Abarrotes"), commit=True
    )
    return ProductoRepository(db).crear(
        ProductoCreate(
            categoria_id=categoria.id,
            nombre="Arroz",
            sku="ARR-001",
            precio_caja=Decimal("20.00"),
            precio_unidad=Decimal("1.00"),
            unidades_por_caja=20,
        ),
        commit=True,
    )


def test_crear_y_consultar_pedido_b2b(db):
    cliente = _cliente(db)
    producto = _producto(db)
    repo = PedidoB2BRepository(db)
    pedido = repo.crear(
        PedidoB2BCreate(
            cliente_id=cliente.id,
            notas="Entrega lunes",
            lineas=[
                LineaPedidoB2BCreate(
                    producto_id=producto.id,
                    tipo_empaque=TipoEmpaque.CAJA,
                    cantidad=Decimal("2.00"),
                    subtotal=Decimal("40.00"),
                    orden=1,
                )
            ],
        ),
        commit=True,
    )

    assert pedido.id is not None
    assert pedido.estado == EstadoPedido.PENDIENTE
    assert pedido.total_estimado == Decimal("0.00")
    assert pedido.factura_generada_id is None
    cargado = repo.get_con_lineas(pedido.id)
    assert cargado is not None
    assert cargado.cliente_id == cliente.id
    assert len(cargado.lineas) == 1
    assert len(repo.listar(cliente_id=cliente.id)) == 1


def test_actualizar_pedido_solo_cambia_campos_enviados(db):
    cliente = _cliente(db)
    repo = PedidoB2BRepository(db)
    pedido = repo.crear(
        PedidoB2BCreate(cliente_id=cliente.id, notas="Inicial"),
        commit=True,
    )

    repo.actualizar(
        pedido,
        PedidoB2BUpdate(estado=EstadoPedido.PROCESANDO, total_estimado=Decimal("25.50")),
        commit=True,
    )

    assert pedido.estado == EstadoPedido.PROCESANDO
    assert pedido.total_estimado == Decimal("25.50")
    assert pedido.notas == "Inicial"


def test_commit_false_solo_hace_flush_y_permite_rollback(db):
    cliente = _cliente(db)
    repo = PedidoB2BRepository(db)
    pedido = repo.crear(
        PedidoB2BCreate(cliente_id=cliente.id, notas="Transaccional"),
        commit=False,
    )
    assert pedido.id is not None
    db.rollback()
    assert repo.get(pedido.id) is None


def test_pedido_con_cliente_inexistente_falla(db):
    with pytest.raises(IntegridadPedidoError):
        PedidoB2BRepository(db).crear(
            PedidoB2BCreate(cliente_id=99999), commit=True
        )


def test_crear_listar_y_actualizar_linea_pedido(db):
    cliente = _cliente(db)
    producto = _producto(db)
    pedido = PedidoB2BRepository(db).crear(
        PedidoB2BCreate(cliente_id=cliente.id), commit=True
    )
    repo = LineaPedidoB2BRepository(db)
    linea = repo.crear(
        pedido.id,
        LineaPedidoB2BCreate(
            producto_id=producto.id,
            tipo_empaque=TipoEmpaque.CAJA,
            cantidad=Decimal("2.00"),
            subtotal=Decimal("40.00"),
            orden=1,
        ),
        commit=True,
    )

    assert linea.id is not None
    assert repo.listar_por_pedido(pedido.id)[0].subtotal == Decimal("40.00")

    repo.actualizar(linea, LineaPedidoB2BUpdate(cantidad=Decimal("3.00")), commit=True)
    assert linea.cantidad == Decimal("3.00")
    assert linea.subtotal == Decimal("40.00")


def test_no_permite_dos_lineas_con_mismo_orden_en_pedido(db):
    cliente = _cliente(db)
    producto = _producto(db)
    pedido = PedidoB2BRepository(db).crear(
        PedidoB2BCreate(cliente_id=cliente.id), commit=True
    )
    repo = LineaPedidoB2BRepository(db)
    datos = LineaPedidoB2BCreate(
        producto_id=producto.id,
        tipo_empaque=TipoEmpaque.UNIDAD,
        cantidad=Decimal("1.00"),
        subtotal=Decimal("1.00"),
        orden=0,
    )
    repo.crear(pedido.id, datos, commit=True)

    with pytest.raises(IntegridadPedidoError):
        repo.crear(pedido.id, datos, commit=True)


def test_esquemas_rechazan_cantidad_cero_y_subtotal_negativo():
    with pytest.raises(ValidationError):
        LineaPedidoB2BCreate(
            producto_id=1,
            cantidad=Decimal("0"),
            subtotal=Decimal("1.00"),
            orden=0,
        )
    with pytest.raises(ValidationError):
        LineaPedidoB2BCreate(
            producto_id=1,
            cantidad=Decimal("1"),
            subtotal=Decimal("-1.00"),
            orden=0,
        )
