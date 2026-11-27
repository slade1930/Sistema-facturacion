import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra todas las tablas)
from app.api.v1.endpoints.ml.recomendaciones import recomendar
from app.db.base import Base
from app.models.catalogo import (
    Categoria,
    ClienteB2B,
    LineaPedidoB2B,
    PedidoB2B,
    Producto,
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
    sesion = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


def _sembrar(db, n_productos=5, inactivos=()):
    """Crea categoría, cliente y productos. Devuelve la lista de ids de producto."""
    cat = Categoria(nombre="Galletas")
    cli = ClienteB2B(nombre_empresa="Super", ruc="1-1-1", email_contacto="a@b.com")
    db.add_all([cat, cli])
    db.flush()
    productos = [
        Producto(
            categoria_id=cat.id,
            nombre=f"Producto {i}",
            sku=f"SKU-{i}",
            precio_caja=24,
            precio_unidad=1,
            estado_activo=(i not in inactivos),
        )
        for i in range(n_productos)
    ]
    db.add_all(productos)
    db.commit()
    return cli.id, [p.id for p in productos]


def _pedido(db, cliente_id, productos):
    db.add(
        PedidoB2B(
            cliente_id=cliente_id,
            lineas=[
                LineaPedidoB2B(producto_id=p, cantidad=1, subtotal=1, orden=i + 1)
                for i, p in enumerate(productos)
            ],
        )
    )
    db.commit()


def _ids(respuesta):
    return [r["producto_id"] for r in respuesta["resultado"]]


def test_ids_invalidos_devuelven_error_con_formato_detail_code(db):
    for texto in ["abc", "", "1,,x", "0", "-3"]:
        resp = recomendar(producto_ids=texto, n=5, db=db)
        assert resp.status_code == 400
        cuerpo = json.loads(resp.body)
        assert cuerpo["code"] == "producto_ids_invalidos"
        assert "detail" in cuerpo


def test_sin_historial_responde_sin_evaluar_y_lista_vacia(db):
    resp = recomendar(producto_ids="1,2", n=5, db=db)
    assert resp["evaluado"] is False
    assert resp["modelo"] == "sin evaluar"
    assert resp["resultado"] == []


def test_no_recomienda_lo_que_ya_esta_en_el_carrito(db):
    cliente, ids = _sembrar(db)
    for _ in range(3):
        _pedido(db, cliente, [ids[0], ids[1], ids[2]])
    resp = recomendar(producto_ids=str(ids[0]), n=5, db=db)
    assert ids[0] not in _ids(resp)
    assert set(_ids(resp)) <= {ids[1], ids[2], ids[3], ids[4]}


def test_no_recomienda_productos_inactivos(db):
    cliente, ids = _sembrar(db, inactivos={2})
    for _ in range(3):
        _pedido(db, cliente, [ids[0], ids[1], ids[2]])
    resp = recomendar(producto_ids=str(ids[0]), n=5, db=db)
    assert ids[2] not in _ids(resp)
    assert ids[1] in _ids(resp)


def test_respeta_n(db):
    cliente, ids = _sembrar(db, n_productos=6)
    for _ in range(3):
        _pedido(db, cliente, ids)
    resp = recomendar(producto_ids=str(ids[0]), n=2, db=db)
    assert len(resp["resultado"]) <= 2