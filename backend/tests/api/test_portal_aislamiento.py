"""Pruebas de aislamiento entre empresas y filtro por sector."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Producto, SectorEmpresa

REGISTRO_TEC = {
    "nombre_empresa": "Aislamiento Tecnologia PR",
    "ruc": "RUC-AISL-TEC-PR",
    "direccion": "Calle 1",
    "telefono": "60000001",
    "correo": "aislamiento@ejemplo.local",
    "sucursal": "Central",
    "contrasena": "Clave1234",
    "sector": "tecnologia",
}
REGISTRO_TUR = REGISTRO_TEC | {
    "nombre_empresa": "Aislamiento Turismo PR",
    "ruc": "RUC-AISL-TUR-PR",
    "sector": "turismo",
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


@pytest.fixture
def empresas(client: TestClient):
    tec = client.post("/api/v1/auth/registro", json=REGISTRO_TEC)
    tur = client.post("/api/v1/auth/registro", json=REGISTRO_TUR)
    assert tec.status_code == 200, tec.text
    assert tur.status_code == 200, tur.text
    return tec.json(), tur.json()


def _headers(token: str) -> dict:
    return {"Authorization": "Bearer " + token}


def _sembrar_catalogo(db: Session):
    tec = Categoria(
        nombre="Cat Aislamiento Tecnologia", sector=SectorEmpresa.TECNOLOGIA
    )
    tur = Categoria(
        nombre="Cat Aislamiento Turismo", sector=SectorEmpresa.TURISMO
    )
    sin_sector = Categoria(nombre="Cat Aislamiento Sin Sector")
    prod_tur = Producto(
        categoria=tur,
        nombre="Prod Aislamiento Turismo",
        sku="SKU-AISL-TUR",
        precio_caja=Decimal("20.00"),
        precio_unidad=Decimal("2.00"),
        unidades_por_caja=10,
    )
    prod_tec = Producto(
        categoria=tec,
        nombre="Prod Aislamiento Tecnologia",
        sku="SKU-AISL-TEC",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
    )
    db.add_all([tec, tur, sin_sector, prod_tur, prod_tec])
    db.flush()
    return tec, tur, sin_sector, prod_tur, prod_tec


def test_categorias_y_productos_se_filtran_por_sector(client, db, empresas):
    tec, tur, sin_sector, prod_tur, prod_tec = _sembrar_catalogo(db)
    empresa_tec = empresas[0]

    visibles = client.get(
        "/api/v1/categorias", headers=_headers(empresa_tec["token"])
    ).json()
    ids = {categoria["id"] for categoria in visibles}
    assert tec.id in ids
    assert tur.id not in ids
    assert sin_sector.id not in ids

    productos = client.get(
        "/api/v1/productos", headers=_headers(empresa_tec["token"])
    ).json()
    ids_productos = {producto["id"] for producto in productos}
    assert prod_tec.id in ids_productos
    assert prod_tur.id not in ids_productos

    assert (
        client.get(
            f"/api/v1/productos/{prod_tur.id}",
            headers=_headers(empresa_tec["token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/productos/{prod_tur.id}",
            headers=_headers(empresas[1]["token"]),
        ).status_code
        == 200
    )

    busqueda = client.get(
        "/api/v1/catalogo/buscar",
        params={"q": "Aislamiento"},
        headers=_headers(empresa_tec["token"]),
    ).json()
    assert all(
        categoria["id"] != tur.id for categoria in busqueda["categorias"]
    )


def test_empresa_ve_solo_sus_clientes_y_facturas(client, db, empresas):
    tec, tur = empresas
    factura = client.post(
        "/api/v1/facturas",
        json={
            "cliente_nombre": REGISTRO_TUR["nombre_empresa"],
            "cliente_ruc": REGISTRO_TUR["ruc"],
            "lineas": [
                {
                    "descripcion": "Servicio",
                    "cantidad": "1",
                    "precio_unitario": "10.00",
                }
            ],
        },
    )
    assert factura.status_code == 201, factura.text
    factura_id = factura.json()["id"]

    assert client.get(
        f"/api/v1/clientes/{tur['empresa']['id']}",
        headers=_headers(tec["token"]),
    ).status_code == 404
    assert [
        cliente["id"]
        for cliente in client.get(
            "/api/v1/clientes", headers=_headers(tec["token"])
        ).json()
    ] == [tec["empresa"]["id"]]

    pedido_ajeno = client.post(
        "/api/v1/pedidos",
        headers=_headers(tec["token"]),
        json={"cliente_id": tur["empresa"]["id"], "lineas": []},
    )
    assert pedido_ajeno.status_code == 403

    assert (
        client.get(
            f"/api/v1/facturas/{factura_id}", headers=_headers(tec["token"])
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/facturas/{factura_id}/pdf",
            headers=_headers(tec["token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/facturas/{factura_id}", headers=_headers(tur["token"])
        ).status_code
        == 200
    )


def test_configuracion_y_escrituras_son_admin_only(client, empresas):
    headers = _headers(empresas[0]["token"])
    factura = {
        "cliente_nombre": REGISTRO_TEC["nombre_empresa"],
        "cliente_ruc": REGISTRO_TEC["ruc"],
        "lineas": [
            {
                "descripcion": "Servicio",
                "cantidad": "1",
                "precio_unitario": "10.00",
            }
        ],
    }
    rutas = [
        ("get", "/api/v1/configuracion", None),
        ("post", "/api/v1/facturas", factura),
        ("get", "/api/v1/pedidos/por-facturar", None),
        ("get", "/api/v1/ml/pronostico", None),
        ("post", "/api/v1/categorias", {"nombre": "Categoria empresa"}),
        ("get", "/api/v1/admin/resumen", None),
    ]
    for metodo, ruta, cuerpo in rutas:
        if cuerpo is None:
            respuesta = getattr(client, metodo)(ruta, headers=headers)
        else:
            respuesta = getattr(client, metodo)(
                ruta, headers=headers, json=cuerpo
            )
        assert respuesta.status_code == 403, (ruta, respuesta.text)

    assert (
        client.post(
            "/api/v1/ml/anomalias/evaluar/1", headers=headers
        ).status_code
        == 403
    )

    recomendaciones = client.get(
        "/api/v1/ml/recomendaciones", headers=headers
    )
    assert recomendaciones.status_code == 200
