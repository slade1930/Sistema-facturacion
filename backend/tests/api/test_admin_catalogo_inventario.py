"""Catálogo administrado, existencias iniciales y columnas de ventas."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalogo import (
    ClienteB2B,
    EstadoPedido,
    LineaPedidoB2B,
    PedidoB2B,
    TipoEmpaque,
)


@pytest.fixture
def db(client) -> Session:
    from app.api.v1.deps import get_db
    from app.main import app

    generador = app.dependency_overrides[get_db]()
    sesion = next(generador)
    try:
        yield sesion
    finally:
        generador.close()


def _d(valor) -> Decimal:
    return Decimal(str(valor))


def _crear_categoria(client, nombre: str, sector: str) -> int:
    respuesta = client.post(
        "/api/v1/admin/catalogo/categorias",
        json={"nombre": nombre, "sector": sector},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_producto(
    client,
    categoria_id: int,
    sku: str,
    existencias: str | None = None,
    nombre: str = "Producto Admin Catálogo",
) -> int:
    datos = {
        "categoria_id": categoria_id,
        "nombre": nombre,
        "sku": sku,
        "precio_caja": "25.00",
        "precio_unidad": "2.50",
        "unidades_por_caja": 10,
    }
    if existencias is not None:
        datos["existencias_iniciales"] = existencias
    respuesta = client.post("/api/v1/admin/catalogo/productos", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_admin_categorias_con_sector_y_total_de_productos(client):
    categoria_id = _crear_categoria(client, "Cat Admin Catálogo", "tecnologia")

    listado = client.get(
        "/api/v1/admin/catalogo/categorias",
        params={"sector": "tecnologia", "busqueda": "Admin Catálogo"},
    )
    assert listado.status_code == 200, listado.text
    assert listado.json()["total"] == 1
    assert listado.json()["items"][0]["id"] == categoria_id
    assert listado.json()["items"][0]["total_productos"] == 0

    _crear_producto(client, categoria_id, "SKU-ADMIN-CAT-1")
    detalle = client.get(f"/api/v1/admin/catalogo/categorias/{categoria_id}")
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["total_productos"] == 1

    actualizada = client.put(
        f"/api/v1/admin/catalogo/categorias/{categoria_id}",
        json={"nombre": "Cat Admin Renombrada", "sector": "turismo"},
    )
    assert actualizada.status_code == 200, actualizada.text
    assert actualizada.json()["nombre"] == "Cat Admin Renombrada"
    assert actualizada.json()["sector"] == "turismo"

    por_sector = client.get(
        "/api/v1/admin/catalogo/categorias", params={"sector": "turismo"}
    )
    assert por_sector.status_code == 200, por_sector.text
    assert por_sector.json()["total"] == 1
    assert por_sector.json()["items"][0]["id"] == categoria_id


def test_admin_producto_guarda_existencias_iniciales_como_entrada(client):
    categoria_id = _crear_categoria(client, "Cat Admin Entrada", "tecnologia")
    producto_id = _crear_producto(
        client, categoria_id, "SKU-ADMIN-ENTRADA", existencias="12.50"
    )

    detalle = client.get(f"/api/v1/admin/catalogo/productos/{producto_id}")
    assert detalle.status_code == 200, detalle.text
    datos = detalle.json()
    assert datos["categoria_nombre"] == "Cat Admin Entrada"
    assert datos["sector"] == "tecnologia"
    assert _d(datos["existencias"]) == Decimal("12.50")
    assert _d(datos["stock_minimo"]) == Decimal("0.00")

    movimientos = client.get(
        "/api/v1/admin/inventario/movimientos",
        params={"producto_id": producto_id, "tipo": "entrada"},
    )
    assert movimientos.status_code == 200, movimientos.text
    assert movimientos.json()["total"] == 1
    movimiento = movimientos.json()["items"][0]
    assert movimiento["producto_id"] == producto_id
    assert movimiento["tipo"] == "entrada"
    assert _d(movimiento["cantidad"]) == Decimal("12.50")
    assert "Existencias iniciales" in movimiento["motivo"]

    globales = client.get("/api/v1/admin/inventario/movimientos")
    assert globales.status_code == 200, globales.text
    assert any(item["id"] == movimiento["id"] for item in globales.json()["items"])


def test_admin_actualizar_producto_exige_categoria_y_registra_ajuste(client):
    categoria_id = _crear_categoria(client, "Cat Admin Ajuste", "turismo")
    producto_id = _crear_producto(
        client, categoria_id, "SKU-ADMIN-AJUSTE", existencias="10.00"
    )

    sin_categoria = client.put(
        f"/api/v1/admin/catalogo/productos/{producto_id}",
        json={"nombre": "Cambio sin categoría"},
    )
    assert sin_categoria.status_code == 422, sin_categoria.text

    ajuste = client.put(
        f"/api/v1/admin/catalogo/productos/{producto_id}",
        json={"categoria_id": categoria_id, "existencias": "4.00"},
    )
    assert ajuste.status_code == 200, ajuste.text
    assert _d(ajuste.json()["existencias"]) == Decimal("4.00")

    movimientos = client.get(
        "/api/v1/admin/inventario/movimientos",
        params={"producto_id": producto_id, "tipo": "ajuste"},
    )
    assert movimientos.status_code == 200, movimientos.text
    assert movimientos.json()["total"] == 1
    assert _d(movimientos.json()["items"][0]["cantidad"]) == Decimal("6.00")

    desactivado = client.put(
        f"/api/v1/admin/catalogo/productos/{producto_id}/estado",
        json={"activo": False},
    )
    assert desactivado.status_code == 200, desactivado.text
    assert desactivado.json()["estado_activo"] is False

    activos = client.get(
        "/api/v1/admin/catalogo/productos",
        params={"busqueda": "SKU-ADMIN-AJUSTE", "solo_activos": True},
    )
    assert activos.status_code == 200, activos.text
    assert activos.json()["total"] == 0

    todos = client.get(
        "/api/v1/admin/catalogo/productos",
        params={"busqueda": "SKU-ADMIN-AJUSTE", "solo_activos": False},
    )
    assert todos.status_code == 200, todos.text
    assert todos.json()["total"] == 1


def test_admin_catalogo_muestra_stock_y_ventas_del_periodo(client, db: Session):
    categoria_id = _crear_categoria(client, "Cat Admin Ventas", "tecnologia")
    producto_id = _crear_producto(
        client, categoria_id, "SKU-ADMIN-VENTAS", existencias="12.50"
    )

    cliente = ClienteB2B(
        nombre_empresa="Cliente Admin Ventas",
        ruc="RUC-ADMIN-VENTAS",
        email_contacto="ventas-admin@ejemplo.local",
        sector="tecnologia",
        activo=True,
    )
    db.add(cliente)
    db.flush()
    pedido = PedidoB2B(
        cliente_id=cliente.id,
        estado=EstadoPedido.PENDIENTE,
        total_estimado=Decimal("50.00"),
        notas="Pedido admin ventas",
        fecha_creacion=datetime.now(timezone.utc),
    )
    db.add(pedido)
    db.flush()
    db.add(
        LineaPedidoB2B(
            pedido_id=pedido.id,
            producto_id=producto_id,
            tipo_empaque=TipoEmpaque.CAJA,
            cantidad=Decimal("2.00"),
            subtotal=Decimal("50.00"),
            orden=1,
        )
    )
    db.flush()

    hoy = datetime.now(timezone.utc).date()
    respuesta = client.get(
        f"/api/v1/admin/catalogo/productos/{producto_id}",
        params={"desde": hoy.isoformat(), "hasta": hoy.isoformat()},
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert _d(datos["existencias"]) == Decimal("12.50")
    assert _d(datos["ventas_unidades"]) == Decimal("20.00")
    assert _d(datos["ventas_monto"]) == Decimal("50.00")
    assert datos["pedidos"] == 1
