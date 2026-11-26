"""Pruebas del endpoint POST /carrito/calcular (sin persistencia)."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Producto


@pytest.fixture
def db(client) -> Session:
    """Sesión del cliente de prueba: lo que se siembra se limpia con su rollback."""
    from app.db.session import get_db
    from app.main import app

    generador = app.dependency_overrides[get_db]()
    sesion = next(generador)
    try:
        yield sesion
    finally:
        generador.close()


def _sembrar(db: Session):
    categoria = Categoria(nombre="Cat Carrito API")
    producto = Producto(
        categoria=categoria,
        nombre="Prod Carrito API",
        sku="SKU-CAR-API-1",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
        permite_media_caja=True,
        precio_media_caja=Decimal("5.50"),
        aplica_itbms=True,
    )
    sin_media = Producto(
        categoria=categoria,
        nombre="Prod Sin Media API",
        sku="SKU-CAR-API-2",
        precio_caja=Decimal("20.00"),
        precio_unidad=Decimal("2.00"),
        unidades_por_caja=5,
        permite_media_caja=False,
        precio_media_caja=None,
        aplica_itbms=False,
    )
    inactivo = Producto(
        categoria=categoria,
        nombre="Prod Inactivo API",
        sku="SKU-CAR-API-3",
        precio_caja=Decimal("30.00"),
        precio_unidad=Decimal("3.00"),
        estado_activo=False,
    )
    db.add_all([categoria, producto, sin_media, inactivo])
    db.flush()
    return producto, sin_media, inactivo


def test_calcular_carrito_caja_y_unidad(client, db):
    producto, _, _ = _sembrar(db)

    respuesta = client.post(
        "/api/v1/carrito/calcular",
        json={
            "lineas": [
                {
                    "producto_id": producto.id,
                    "tipo_empaque": "caja",
                    "cantidad": "2",
                },
                {
                    "producto_id": producto.id,
                    "tipo_empaque": "unidad",
                    "cantidad": "5",
                },
            ]
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert len(datos["lineas"]) == 2
    assert datos["lineas"][0]["subtotal"] == "20.00"
    assert datos["lineas"][1]["subtotal"] == "5.00"
    # 2 cajas x 10 + 5 unidades x 1 = 25.00 gravado -> ITBMS 7% = 1.75
    assert datos["subtotal"] == "25.00"
    assert datos["base_gravada"] == "25.00"
    assert datos["itbms"] == "1.75"
    assert datos["total"] == "26.75"


def test_calcular_carrito_media_caja_y_exento(client, db):
    producto, sin_media, _ = _sembrar(db)

    respuesta = client.post(
        "/api/v1/carrito/calcular",
        json={
            "lineas": [
                {
                    "producto_id": producto.id,
                    "tipo_empaque": "media_caja",
                    "cantidad": "2",
                },
                {
                    "producto_id": sin_media.id,
                    "tipo_empaque": "caja",
                    "cantidad": "1",
                },
            ]
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    # media caja: 2 x 5.50 = 11.00 (gravada); sin_media: 1 x 20 = 20.00 (exenta)
    assert datos["lineas"][0]["subtotal"] == "11.00"
    assert datos["lineas"][1]["subtotal"] == "20.00"
    assert datos["base_gravada"] == "11.00"
    assert datos["base_exenta"] == "20.00"
    assert datos["itbms"] == "0.77"  # 7% de 11.00
    assert datos["total"] == "31.77"


def test_calcular_carrito_producto_inexistente(client, db):
    _sembrar(db)

    respuesta = client.post(
        "/api/v1/carrito/calcular",
        json={
            "lineas": [
                {"producto_id": 999999, "tipo_empaque": "caja", "cantidad": "1"}
            ]
        },
    )

    assert respuesta.status_code == 404


def test_calcular_carrito_media_caja_no_permitida(client, db):
    _, sin_media, _ = _sembrar(db)

    respuesta = client.post(
        "/api/v1/carrito/calcular",
        json={
            "lineas": [
                {
                    "producto_id": sin_media.id,
                    "tipo_empaque": "media_caja",
                    "cantidad": "1",
                }
            ]
        },
    )

    assert respuesta.status_code == 422, respuesta.text


def test_calcular_carrito_producto_inactivo(client, db):
    _, _, inactivo = _sembrar(db)

    respuesta = client.post(
        "/api/v1/carrito/calcular",
        json={
            "lineas": [
                {
                    "producto_id": inactivo.id,
                    "tipo_empaque": "caja",
                    "cantidad": "1",
                }
            ]
        },
    )

    assert respuesta.status_code == 422, respuesta.text


def test_calcular_carrito_sin_lineas(client):
    respuesta = client.post("/api/v1/carrito/calcular", json={"lineas": []})

    assert respuesta.status_code == 422
