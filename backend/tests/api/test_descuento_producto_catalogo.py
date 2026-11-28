"""Pruebas de extremo a extremo del descuento por producto en el catálogo."""

import secrets
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, ClienteB2B, Producto, SectorEmpresa
from app.models.seguridad import Cuenta, RolCuenta
from app.services.auth import crear_sesion, hash_clave
from app.services.totales import calcular_totales

DESCUENTO_PRUEBA = Decimal("15.00")
SIN_DESCUENTO = Decimal("0.00")
CAMPOS_TOTALES = (
    "subtotal",
    "descuento_total",
    "base_gravada",
    "base_exenta",
    "itbms",
    "total",
)


@pytest.fixture
def db(client) -> Session:
    """Sesión del cliente de prueba; la fixture client se encarga del rollback."""
    from app.db.session import get_db
    from app.main import app

    generador = app.dependency_overrides[get_db]()
    sesion = next(generador)
    try:
        yield sesion
    finally:
        generador.close()


def _decimal(valor) -> Decimal:
    return Decimal(str(valor))


def _sembrar_producto(db: Session, descuento_pct: Decimal) -> Producto:
    sufijo = uuid4().hex[:10]
    categoria = Categoria(
        nombre=f"Cat Descuento Catalogo {sufijo}",
        sector=SectorEmpresa.TECNOLOGIA,
    )
    producto = Producto(
        categoria=categoria,
        nombre=f"Prod Descuento Catalogo {sufijo}",
        sku=f"SKU-DESC-CAT-{sufijo}",
        precio_caja=Decimal("100.00"),
        precio_unidad=Decimal("12.00"),
        precio_media_caja=Decimal("55.00"),
        permite_media_caja=True,
        unidades_por_caja=4,
        aplica_itbms=True,
        descuento_pct=descuento_pct,
    )
    db.add_all([categoria, producto])
    db.flush()
    return producto


def _empresa_autenticada(db: Session) -> dict[str, str]:
    """Devuelve la cabecera de una empresa; la clave se genera en memoria."""
    sufijo = uuid4().hex[:10]
    cliente = ClienteB2B(
        nombre_empresa=f"Empresa Descuento {sufijo}",
        ruc=f"155700000-2-2026-{sufijo}",
        email_contacto=f"descuento-{sufijo}@ejemplo.local",
        sector=SectorEmpresa.TECNOLOGIA,
        activo=True,
    )
    db.add(cliente)
    db.flush()

    cuenta = Cuenta(
        nombre_usuario=f"empresa-descuento-{sufijo}",
        password_hash=hash_clave(secrets.token_urlsafe(16)),
        rol=RolCuenta.EMPRESA,
        cliente_id=cliente.id,
        activo=True,
        debe_cambiar_clave=False,
    )
    db.add(cuenta)
    db.flush()

    token, _ = crear_sesion(db, cuenta)
    return {"Authorization": f"Bearer {token}"}


def _lineas_carrito(producto_id: int) -> list[dict]:
    return [
        {"producto_id": producto_id, "tipo_empaque": "caja", "cantidad": "2"},
        {"producto_id": producto_id, "tipo_empaque": "unidad", "cantidad": "3"},
        {"producto_id": producto_id, "tipo_empaque": "media_caja", "cantidad": "1"},
    ]


def _lineas_para_servicio(producto: Producto, descuento_pct: Decimal) -> list[dict]:
    """Líneas equivalentes a las que arma el endpoint del carrito."""
    return [
        {
            "cantidad": Decimal("2"),
            "precio_unitario": producto.precio_caja,
            "precio_unidad": None,
            "descuento_pct": descuento_pct,
            "gravada": True,
            "cobrar_por": "caja",
        },
        {
            "cantidad": Decimal("3"),
            "precio_unitario": producto.precio_unidad,
            "precio_unidad": producto.precio_unidad,
            "descuento_pct": descuento_pct,
            "gravada": True,
            "cobrar_por": "unidad",
        },
        {
            "cantidad": Decimal("1"),
            "precio_unitario": producto.precio_media_caja,
            "precio_unidad": None,
            "descuento_pct": descuento_pct,
            "gravada": True,
            "cobrar_por": "unidad",
        },
    ]


def test_carrito_aplica_el_descuento_del_producto(client, db):
    producto = _sembrar_producto(db, DESCUENTO_PRUEBA)

    respuesta = client.post(
        "/api/v1/carrito/calcular",
        json={"lineas": _lineas_carrito(producto.id)},
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    esperado = calcular_totales(
        _lineas_para_servicio(producto, DESCUENTO_PRUEBA),
        portes=Decimal("0.00"),
    )
    for campo in CAMPOS_TOTALES:
        assert _decimal(datos[campo]) == esperado[campo], campo

    # Bruto 291.00 - 15 % = 247.35; ITBMS 7 % = 17.31; total = 264.66.
    assert _decimal(datos["subtotal"]) == Decimal("291.00")
    assert _decimal(datos["descuento_total"]) == Decimal("43.65")
    assert _decimal(datos["base_gravada"]) == Decimal("247.35")
    assert _decimal(datos["base_exenta"]) == Decimal("0.00")
    assert _decimal(datos["itbms"]) == Decimal("17.31")
    assert _decimal(datos["total"]) == Decimal("264.66")
    # El detalle del carrito sigue mostrando el bruto de cada línea.
    assert [linea["subtotal"] for linea in datos["lineas"]] == [
        "200.00",
        "36.00",
        "55.00",
    ]


def test_compra_y_factura_coinciden_con_el_carrito_con_descuento(client, db):
    producto = _sembrar_producto(db, DESCUENTO_PRUEBA)
    cabecera = _empresa_autenticada(db)
    cuerpo = {"lineas": _lineas_carrito(producto.id)}

    carrito = client.post("/api/v1/carrito/calcular", json=cuerpo)
    assert carrito.status_code == 200, carrito.text
    totales_carrito = carrito.json()

    compra = client.post("/api/v1/compras", headers=cabecera, json=cuerpo)
    assert compra.status_code == 201, compra.text
    datos_compra = compra.json()

    factura_resp = client.get(
        f"/api/v1/facturas/{datos_compra['factura_id']}", headers=cabecera
    )
    assert factura_resp.status_code == 200, factura_resp.text
    factura = factura_resp.json()

    assert _decimal(datos_compra["total"]) == _decimal(totales_carrito["total"])
    assert _decimal(factura["total"]) == _decimal(totales_carrito["total"])
    assert _decimal(factura["total"]) == Decimal("264.66")
    for campo in CAMPOS_TOTALES:
        assert _decimal(factura[campo]) == _decimal(totales_carrito[campo]), campo

    lineas_factura = sorted(factura["lineas"], key=lambda linea: linea["orden"])
    assert [
        _decimal(linea["descuento_pct"]) for linea in lineas_factura
    ] == [DESCUENTO_PRUEBA] * 3
    assert [_decimal(linea["monto"]) for linea in lineas_factura] == [
        Decimal("170.00"),
        Decimal("30.60"),
        Decimal("46.75"),
    ]
    assert sum(
        (_decimal(linea["monto"]) for linea in lineas_factura), Decimal("0.00")
    ) == _decimal(totales_carrito["base_gravada"])

    pedido_resp = client.get(
        f"/api/v1/pedidos/{datos_compra['pedido_id']}", headers=cabecera
    )
    assert pedido_resp.status_code == 200, pedido_resp.text
    pedido = pedido_resp.json()
    lineas_pedido = sorted(pedido["lineas"], key=lambda linea: linea["orden"])
    assert [_decimal(linea["subtotal"]) for linea in lineas_pedido] == [
        Decimal("170.00"),
        Decimal("30.60"),
        Decimal("46.75"),
    ]
    # El pedido conserva su diseño: total_estimado es la base neta, sin ITBMS.
    base_neta = _decimal(factura["subtotal"]) - _decimal(
        factura["descuento_total"]
    )
    assert _decimal(pedido["total_estimado"]) == base_neta == Decimal("247.35")


def test_producto_sin_descuento_conserva_el_total_historico(client, db):
    producto = _sembrar_producto(db, SIN_DESCUENTO)
    cabecera = _empresa_autenticada(db)
    cuerpo = {"lineas": _lineas_carrito(producto.id)}

    carrito = client.post("/api/v1/carrito/calcular", json=cuerpo)
    assert carrito.status_code == 200, carrito.text
    totales_carrito = carrito.json()

    esperado = calcular_totales(
        _lineas_para_servicio(producto, SIN_DESCUENTO),
        portes=Decimal("0.00"),
    )
    for campo in CAMPOS_TOTALES:
        assert _decimal(totales_carrito[campo]) == esperado[campo], campo

    # Sin descuento: 291.00 gravados, ITBMS 20.37 y total 311.37.
    assert _decimal(totales_carrito["descuento_total"]) == Decimal("0.00")
    assert _decimal(totales_carrito["base_gravada"]) == Decimal("291.00")
    assert _decimal(totales_carrito["itbms"]) == Decimal("20.37")
    assert _decimal(totales_carrito["total"]) == Decimal("311.37")

    compra = client.post("/api/v1/compras", headers=cabecera, json=cuerpo)
    assert compra.status_code == 201, compra.text

    factura_resp = client.get(
        f"/api/v1/facturas/{compra.json()['factura_id']}", headers=cabecera
    )
    assert factura_resp.status_code == 200, factura_resp.text
    factura = factura_resp.json()

    assert _decimal(compra.json()["total"]) == _decimal(totales_carrito["total"])
    assert _decimal(factura["total"]) == _decimal(totales_carrito["total"])
    assert len(factura["lineas"]) == 3
    assert all(
        _decimal(linea["descuento_pct"]) == SIN_DESCUENTO
        for linea in factura["lineas"]
    )
