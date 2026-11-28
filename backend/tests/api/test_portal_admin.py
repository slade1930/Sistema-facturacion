"""Pruebas de los endpoints de inventario y resumen de administración."""

import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Producto, SectorEmpresa


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


def _producto(db: Session):
    categoria = Categoria(
        nombre="Cat Admin Portal", sector=SectorEmpresa.TECNOLOGIA
    )
    producto = Producto(
        categoria=categoria,
        nombre="Prod Admin Portal",
        sku="SKU-ADMIN-PORTAL",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
    )
    db.add_all([categoria, producto])
    db.flush()
    return producto


def test_admin_ajusta_inventario_y_ve_movimientos(client, db: Session):
    producto = _producto(db)
    respuesta = client.put(
        f"/api/v1/admin/inventario/{producto.id}",
        json={
            "existencias": "20.00",
            "stock_minimo": "3.00",
            "motivo": "Carga inicial",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["existencias"] == "20.00"
    assert datos["stock_minimo"] == "3.00"

    listado = client.get("/api/v1/admin/inventario").json()
    assert any(item["producto_id"] == producto.id for item in listado)

    movimientos = client.get(
        f"/api/v1/admin/inventario/{producto.id}/movimientos"
    ).json()
    assert len(movimientos) == 1
    assert movimientos[0]["tipo"] == "ajuste"
    assert movimientos[0]["motivo"] == "Carga inicial"


def test_resumen_admin_y_acceso_de_empresa(client):
    respuesta = client.get("/api/v1/admin/resumen")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    for clave in (
        "total_empresas",
        "total_pedidos",
        "total_facturas",
        "total_facturado",
        "productos_bajo_stock",
    ):
        assert clave in datos

    registro = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre_empresa": "Admin Portal Prueba",
            "ruc": "RUC-ADMIN-PORTAL",
            "direccion": "Avenida Central",
            "telefono": "60001111",
            "correo": "admin@ejemplo.local",
            "sucursal": "Central",
            "contrasena": "Clave1234",
            "sector": "tecnologia",
        },
    )
    assert registro.status_code == 200, registro.text
    headers = {"Authorization": "Bearer " + registro.json()["token"]}
    assert client.get("/api/v1/admin/resumen", headers=headers).status_code == 403
