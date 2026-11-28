"""Pruebas de la compra con factura automática, stock e idempotencia."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogo import (
    Categoria,
    PedidoB2B,
    Producto,
    SectorEmpresa,
)
from app.models.facturacion import Factura
from app.models.inventario import Inventario, MovimientoInventario, TipoMovimiento

REGISTRO = {
    "nombre_empresa": "Compra Portal Prueba",
    "ruc": "RUC-COMPRA-PRUEBA",
    "direccion": "Avenida Central",
    "telefono": "60009999",
    "correo": "compra@ejemplo.local",
    "sucursal": "Central",
    "contrasena": "Clave1234",
    "sector": "tecnologia",
}


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


def _sembrar(db: Session):
    categoria = Categoria(
        nombre="Cat Compra Portal", sector=SectorEmpresa.TECNOLOGIA
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Compra Portal",
        sku="SKU-COMPRA-PORTAL",
        precio_caja=Decimal("100.00"),
        precio_unidad=Decimal("12.00"),
        unidades_por_caja=10,
        permite_media_caja=True,
        precio_media_caja=Decimal("55.00"),
        aplica_itbms=True,
    )
    otro = Producto(
        categoria=categoria,
        nombre="Prod Compra Sin Stock",
        sku="SKU-COMPRA-PORTAL-2",
        precio_caja=Decimal("50.00"),
        precio_unidad=Decimal("5.00"),
        unidades_por_caja=10,
    )
    db.add_all([categoria, producto, otro])
    db.flush()
    db.add_all(
        [
            Inventario(
                producto_id=producto.id,
                existencias=Decimal("15.00"),
                stock_minimo=Decimal("5.00"),
            ),
            Inventario(
                producto_id=otro.id,
                existencias=Decimal("0.00"),
                stock_minimo=Decimal("0.00"),
            ),
        ]
    )
    db.flush()
    return producto, otro


def _empresa(client: TestClient):
    respuesta = client.post("/api/v1/auth/registro", json=REGISTRO)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    return datos, {"Authorization": "Bearer " + datos["token"]}


def test_compra_crea_factura_y_descuenta_stock(client, db: Session):
    producto, _ = _sembrar(db)
    datos, headers = _empresa(client)

    respuesta = client.post(
        "/api/v1/compras",
        headers=headers,
        json={
            "lineas": [
                {
                    "producto_id": producto.id,
                    "tipo_empaque": "media_caja",
                    "cantidad": "1",
                }
            ]
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    compra = respuesta.json()
    assert compra["reutilizada"] is False

    factura = db.get(Factura, compra["factura_id"])
    pedido = db.get(PedidoB2B, compra["pedido_id"])
    assert factura.cliente_id == datos["empresa"]["id"]
    assert pedido.cliente_id == datos["empresa"]["id"]
    assert factura.pedido_origen[0].id == pedido.id

    db.expire_all()
    inventario = db.get(Inventario, producto.id)
    assert inventario.existencias == Decimal("10.00")
    movimiento = db.scalar(
        select(MovimientoInventario).where(
            MovimientoInventario.factura_id == factura.id
        )
    )
    assert movimiento.tipo == TipoMovimiento.SALIDA
    assert movimiento.cantidad == Decimal("5.00")

    pdf = client.get(f"/api/v1/facturas/{factura.id}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")


def test_idempotencia_devuelve_la_misma_factura(client, db: Session):
    producto, _ = _sembrar(db)
    _, headers = _empresa(client)
    cuerpo = {
        "lineas": [
            {
                "producto_id": producto.id,
                "tipo_empaque": "unidad",
                "cantidad": "2",
            }
        ],
        "clave_idempotencia": "clave-unic-prueba",
    }

    primera = client.post("/api/v1/compras", headers=headers, json=cuerpo)
    segunda = client.post("/api/v1/compras", headers=headers, json=cuerpo)
    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 201, segunda.text
    assert primera.json()["factura_id"] == segunda.json()["factura_id"]
    assert segunda.json()["reutilizada"] is True

    db.expire_all()
    assert db.get(Inventario, producto.id).existencias == Decimal("13.00")
    assert (
        db.scalar(
            select(PedidoB2B).where(
                PedidoB2B.clave_idempotencia == "clave-unic-prueba"
            )
        )
        is not None
    )


def test_compra_rechaza_stock_insuficiente(client, db: Session):
    _, otro = _sembrar(db)
    _, headers = _empresa(client)

    respuesta = client.post(
        "/api/v1/compras",
        headers=headers,
        json={
            "lineas": [
                {
                    "producto_id": otro.id,
                    "tipo_empaque": "caja",
                    "cantidad": "1",
                }
            ]
        },
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "CONFLICT"


def test_compra_no_permite_producto_de_otro_sector(client, db: Session):
    categoria = Categoria(
        nombre="Cat Compra Turismo", sector=SectorEmpresa.TURISMO
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Compra Turismo",
        sku="SKU-COMPRA-TUR-PORTAL",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
    )
    db.add_all([categoria, producto])
    db.flush()
    _, headers = _empresa(client)

    respuesta = client.post(
        "/api/v1/compras",
        headers=headers,
        json={
            "lineas": [
                {
                    "producto_id": producto.id,
                    "tipo_empaque": "caja",
                    "cantidad": "1",
                }
            ]
        },
    )
    assert respuesta.status_code == 404


def test_producto_sin_inventario_no_descuenta_stock(client, db: Session):
    categoria = Categoria(
        nombre="Cat Compra Sin Inventario", sector=SectorEmpresa.TECNOLOGIA
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Compra Sin Inventario",
        sku="SKU-COMPRA-SIN-INV",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
    )
    db.add_all([categoria, producto])
    db.flush()
    _, headers = _empresa(client)

    respuesta = client.post(
        "/api/v1/compras",
        headers=headers,
        json={
            "lineas": [
                {
                    "producto_id": producto.id,
                    "tipo_empaque": "caja",
                    "cantidad": "1",
                }
            ]
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert db.get(Inventario, producto.id) is None
