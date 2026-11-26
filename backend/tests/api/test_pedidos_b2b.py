"""Pruebas de los endpoints de pedidos B2B."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, ClienteB2B, Producto


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
    categoria = Categoria(nombre="Cat Pedidos API")
    cliente = ClienteB2B(
        nombre_empresa="Cliente Pedidos API SAC",
        ruc="155677788-2-2026",
        email_contacto="pedidos@api.com",
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Pedidos API",
        sku="SKU-PED-API-1",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
        permite_media_caja=True,
        precio_media_caja=Decimal("5.50"),
        aplica_itbms=True,
    )
    db.add_all([categoria, cliente, producto])
    db.flush()
    return categoria, cliente, producto


def _payload_pedido(cliente_id: int, producto_id: int) -> dict:
    return {
        "cliente_id": cliente_id,
        "notas": "Pedido de prueba API",
        "lineas": [
            {
                "producto_id": producto_id,
                "tipo_empaque": "caja",
                "cantidad": "2",
                "subtotal": "20.00",
            }
        ],
    }


def test_crear_listar_y_obtener_pedido(client, db):
    _, cliente, producto = _sembrar(db)

    creado = client.post(
        "/api/v1/pedidos-b2b", json=_payload_pedido(cliente.id, producto.id)
    )

    assert creado.status_code == 201, creado.text
    datos = creado.json()
    assert datos["cliente_id"] == cliente.id
    assert datos["estado"] == "pendiente"
    assert len(datos["lineas"]) == 1
    pedido_id = datos["id"]

    listado = client.get("/api/v1/pedidos-b2b")

    assert listado.status_code == 200, listado.text
    pagina = listado.json()
    assert pagina["total"] >= 1
    assert any(item["id"] == pedido_id for item in pagina["items"])

    detalle = client.get(f"/api/v1/pedidos-b2b/{pedido_id}")

    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["id"] == pedido_id
    assert detalle.json()["lineas"][0]["producto_id"] == producto.id


def test_listar_pedidos_filtra_por_cliente_y_estado(client, db):
    _, cliente, producto = _sembrar(db)
    client.post("/api/v1/pedidos-b2b", json=_payload_pedido(cliente.id, producto.id))

    por_cliente = client.get(
        "/api/v1/pedidos-b2b",
        params={"cliente_id": cliente.id, "estado": "pendiente"},
    )

    assert por_cliente.status_code == 200, por_cliente.text
    assert por_cliente.json()["total"] == 1

    por_estado = client.get(
        "/api/v1/pedidos-b2b", params={"estado": "cancelado"}
    )

    assert por_estado.status_code == 200, por_estado.text
    assert por_estado.json()["total"] == 0
    assert por_estado.json()["items"] == []


def test_obtener_pedido_inexistente(client):
    respuesta = client.get("/api/v1/pedidos-b2b/999999")

    assert respuesta.status_code == 404


def test_crear_pedido_cliente_inexistente(client, db):
    _sembrar(db)

    respuesta = client.post(
        "/api/v1/pedidos-b2b",
        json={
            "cliente_id": 999999,
            "lineas": [
                {
                    "producto_id": 1,
                    "tipo_empaque": "caja",
                    "cantidad": "1",
                    "subtotal": "10.00",
                }
            ],
        },
    )

    assert respuesta.status_code == 409, respuesta.text
