"""Devolución de stock al anular facturas, dentro de la misma transacción."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Producto, SectorEmpresa
from app.models.facturacion import EstadoFactura, Factura
from app.models.inventario import Inventario, MovimientoInventario, TipoMovimiento

STOCK_INICIAL = Decimal("20.00")
SALIDA = Decimal("5.00")


@pytest.fixture
def db(client) -> Session:
    from app.db.session import get_db
    from app.main import app

    generador = app.dependency_overrides[get_db]()
    sesion = next(generador)
    try:
        yield sesion
    finally:
        generador.close()


def _sembrar(db: Session, *, con_inventario: bool = True) -> Producto:
    categoria = Categoria(
        nombre="Cat Devolución Endurecimiento", sector=SectorEmpresa.TECNOLOGIA
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Devolución Endurecimiento",
        sku="SKU-DEVOLUCION-ENDURECIMIENTO",
        precio_caja=Decimal("100.00"),
        precio_unidad=Decimal("12.00"),
        unidades_por_caja=10,
        aplica_itbms=True,
    )
    db.add_all([categoria, producto])
    db.flush()
    if con_inventario:
        db.add(
            Inventario(
                producto_id=producto.id,
                existencias=STOCK_INICIAL,
                stock_minimo=Decimal("1.00"),
            )
        )
        db.flush()
    return producto


def _factura(client: TestClient) -> dict:
    respuesta = client.post(
        "/api/v1/facturas",
        json={
            "cliente_nombre": "Cliente Devolución",
            "cliente_ruc": "123456789-1-2026",
            "lineas": [
                {
                    "descripcion": "Producto de prueba",
                    "cantidad": "1",
                    "precio_unitario": "10.00",
                    "gravada": True,
                }
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _registrar_salida(
    db: Session, factura_id: int, producto_id: int, numero_serie: str
) -> None:
    inventario = db.get(Inventario, producto_id)
    if inventario is not None:
        inventario.existencias -= SALIDA
    db.add(
        MovimientoInventario(
            producto_id=producto_id,
            tipo=TipoMovimiento.SALIDA,
            cantidad=SALIDA,
            motivo=f"Compra del portal - factura {numero_serie}"[:200],
            factura_id=factura_id,
            cuenta_id=None,
        )
    )
    db.flush()


def _movimientos(db: Session, factura_id: int) -> list[MovimientoInventario]:
    return list(
        db.scalars(
            select(MovimientoInventario)
            .where(MovimientoInventario.factura_id == factura_id)
            .order_by(MovimientoInventario.id)
        ).all()
    )


def test_endurecimiento_anular_repone_stock(client, db: Session):
    producto = _sembrar(db)
    factura = _factura(client)
    _registrar_salida(db, factura["id"], producto.id, factura["numero_serie"])

    respuesta = client.post(f"/api/v1/facturas/{factura['id']}/anular")

    assert respuesta.status_code == 200, respuesta.text
    db.expire_all()
    assert db.get(Inventario, producto.id).existencias == STOCK_INICIAL
    movimientos = _movimientos(db, factura["id"])
    assert [movimiento.tipo for movimiento in movimientos] == [
        TipoMovimiento.SALIDA,
        TipoMovimiento.ENTRADA,
    ]
    entrada = movimientos[-1]
    assert entrada.cantidad == SALIDA
    assert entrada.motivo == f"anulación de la factura {factura['numero_serie']}"


def test_endurecimiento_doble_anulacion_no_repone_dos_veces(client, db: Session):
    producto = _sembrar(db)
    factura = _factura(client)
    _registrar_salida(db, factura["id"], producto.id, factura["numero_serie"])

    primera = client.post(f"/api/v1/facturas/{factura['id']}/anular")
    segunda = client.post(f"/api/v1/facturas/{factura['id']}/anular")

    assert primera.status_code == 200, primera.text
    assert segunda.status_code == 409
    db.expire_all()
    assert db.get(Inventario, producto.id).existencias == STOCK_INICIAL
    entradas = [
        movimiento
        for movimiento in _movimientos(db, factura["id"])
        if movimiento.tipo == TipoMovimiento.ENTRADA
    ]
    assert len(entradas) == 1


def test_endurecimiento_producto_sin_inventario_no_repone(client, db: Session):
    producto = _sembrar(db, con_inventario=False)
    factura = _factura(client)
    _registrar_salida(db, factura["id"], producto.id, factura["numero_serie"])

    respuesta = client.post(f"/api/v1/facturas/{factura['id']}/anular")

    assert respuesta.status_code == 200, respuesta.text
    db.expire_all()
    assert db.get(Inventario, producto.id) is None
    assert not [
        movimiento
        for movimiento in _movimientos(db, factura["id"])
        if movimiento.tipo == TipoMovimiento.ENTRADA
    ]


def test_endurecimiento_factura_sin_movimientos_no_cambia_stock(client, db: Session):
    producto = _sembrar(db)
    factura = _factura(client)

    respuesta = client.post(f"/api/v1/facturas/{factura['id']}/anular")

    assert respuesta.status_code == 200, respuesta.text
    db.expire_all()
    assert db.get(Inventario, producto.id).existencias == STOCK_INICIAL
    assert _movimientos(db, factura["id"]) == []


def test_endurecimiento_duplicar_factura_no_descuenta_stock(client, db: Session):
    producto = _sembrar(db)
    factura = _factura(client)
    _registrar_salida(db, factura["id"], producto.id, factura["numero_serie"])

    duplicada = client.post(f"/api/v1/facturas/{factura['id']}/duplicar")

    assert duplicada.status_code == 201, duplicada.text
    db.expire_all()
    assert db.get(Inventario, producto.id).existencias == STOCK_INICIAL - SALIDA
    assert _movimientos(db, duplicada.json()["id"]) == []


def test_endurecimiento_fallo_en_devolucion_hace_rollback(
    client, db: Session, monkeypatch: pytest.MonkeyPatch
):
    from app.api.v1.endpoints.facturacion import facturas as modulo_facturas

    producto = _sembrar(db)
    factura = _factura(client)
    _registrar_salida(db, factura["id"], producto.id, factura["numero_serie"])

    def devolver_y_fallar(sesion, factura_id, cuenta_id):
        inventario = sesion.get(Inventario, producto.id)
        inventario.existencias = Decimal("999.00")
        sesion.flush()
        raise RuntimeError("falla controlada de prueba")

    monkeypatch.setattr(modulo_facturas, "devolver_por_factura", devolver_y_fallar)

    with pytest.raises(RuntimeError, match="falla controlada de prueba"):
        client.post(f"/api/v1/facturas/{factura['id']}/anular")

    db.rollback()
    db.expire_all()
    assert db.get(Inventario, producto.id).existencias == STOCK_INICIAL
    assert db.get(Factura, factura["id"]).estado == EstadoFactura.EMITIDA
    assert not [
        movimiento
        for movimiento in _movimientos(db, factura["id"])
        if movimiento.tipo == TipoMovimiento.ENTRADA
    ]
