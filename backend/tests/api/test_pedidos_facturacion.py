"""Pruebas de los endpoints de facturación de pedidos B2B."""
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.catalogo import (
    Categoria,
    ClienteB2B,
    EstadoPedido,
    LineaPedidoB2B,
    PedidoB2B,
    Producto,
    TipoEmpaque,
)


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


def _sembrar(db: Session, estado: EstadoPedido = EstadoPedido.PENDIENTE):
    # Gente, sufijo cortito para no chocar con el UNIQUE si sembramos varias veces.
    sufijo = uuid4().hex[:8]
    categoria = Categoria(nombre=f"Cat Fact Pedidos API-{sufijo}")
    cliente = ClienteB2B(
        nombre_empresa="Cliente Fact Pedidos API SAC",
        ruc=f"155699900-2-2026-{sufijo}",
        email_contacto="factpedidos@api.com",
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Fact Pedidos API",
        sku=f"SKU-FACT-PED-{sufijo}",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
        permite_media_caja=True,
        precio_media_caja=Decimal("5.50"),
        aplica_itbms=True,
    )
    pedido = PedidoB2B(
        cliente=cliente,
        estado=estado,
        total_estimado=Decimal("20.00"),
        notas="Pedido para facturar",
        lineas=[
            LineaPedidoB2B(
                producto=producto,
                tipo_empaque=TipoEmpaque.CAJA,
                cantidad=Decimal("2"),
                subtotal=Decimal("20.00"),
                orden=1,
            )
        ],
    )
    db.add_all([categoria, cliente, producto, pedido])
    db.flush()
    return pedido, cliente, producto


def test_facturar_pedido_exitoso(client, db):
    pedido, _, _ = _sembrar(db)

    respuesta = client.post(f"/api/v1/pedidos/{pedido.id}/facturar")

    assert respuesta.status_code == 201, respuesta.text
    factura = respuesta.json()
    assert factura["numero_serie"].startswith("FAC-")
    assert len(factura["codigo_verificacion"]) == 12
    assert factura["estado"] == "emitida"
    assert factura["cliente_nombre"] == "Cliente Fact Pedidos API SAC"
    # 2 cajas x 10.00 = 20.00 gravado -> ITBMS 7% = 1.40 -> total 21.40
    assert factura["total"] == "21.40"
    assert len(factura["lineas"]) == 1

    pedido_despues = client.get(f"/api/v1/pedidos/{pedido.id}")

    assert pedido_despues.status_code == 200, pedido_despues.text
    datos = pedido_despues.json()
    assert datos["estado"] == "facturado"
    assert datos["factura_generada_id"] == factura["id"]


def test_facturar_pedido_inexistente(client):
    respuesta = client.post("/api/v1/pedidos/999999/facturar")

    assert respuesta.status_code == 404


def test_facturar_pedido_ya_facturado(client, db):
    pedido, _, _ = _sembrar(db)
    client.post(f"/api/v1/pedidos/{pedido.id}/facturar")

    respuesta = client.post(f"/api/v1/pedidos/{pedido.id}/facturar")

    assert respuesta.status_code == 409, respuesta.text


def test_facturar_pedido_cancelado(client, db):
    pedido, _, _ = _sembrar(db, estado=EstadoPedido.CANCELADO)

    respuesta = client.post(f"/api/v1/pedidos/{pedido.id}/facturar")

    assert respuesta.status_code == 409, respuesta.text


def test_listar_pedidos_por_facturar(client, db):
    pendiente, _, _ = _sembrar(db, estado=EstadoPedido.PENDIENTE)
    _sembrar(db, estado=EstadoPedido.CANCELADO)
    procesando, _, _ = _sembrar(db, estado=EstadoPedido.PROCESANDO)

    respuesta = client.get("/api/v1/pedidos/por-facturar")

    assert respuesta.status_code == 200, respuesta.text
    ids = {item["id"] for item in respuesta.json()}
    assert pendiente.id in ids
    assert procesando.id in ids
    assert all(
        item["estado"] in ("pendiente", "procesando")
        and item["factura_generada_id"] is None
        for item in respuesta.json()
    )


def test_listar_pedidos_con_filtros(client, db):
    pedido, cliente, _ = _sembrar(db)

    respuesta = client.get(
        "/api/v1/pedidos",
        params={"cliente_id": cliente.id, "estado": "pendiente"},
    )

    assert respuesta.status_code == 200, respuesta.text
    pagina = respuesta.json()
    assert pagina["total"] == 1
    assert pagina["items"][0]["id"] == pedido.id
