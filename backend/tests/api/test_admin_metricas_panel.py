"""Cálculos del panel con datos conocidos, hechos a mano."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.catalogo import (
    Categoria,
    ClienteB2B,
    EstadoPedido,
    LineaPedidoB2B,
    PedidoB2B,
    Producto,
    SectorEmpresa,
    TipoEmpaque,
)
from app.models.facturacion import (
    CobrarPor,
    CondicionPago,
    EstadoFactura,
    Factura,
    LineaFactura,
)
from app.models.inventario import Inventario
from app.models.seguridad import Cuenta, RolCuenta, Sesion


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


def _sembrar(db: Session):
    ahora = datetime.now(timezone.utc)
    hoy = date.today()
    anterior_mes = hoy.replace(day=1) - timedelta(days=5)

    c1 = ClienteB2B(
        nombre_empresa="Métricas Admin Tecnología",
        ruc="RUC-MET-TEC",
        email_contacto="met-tec@ejemplo.local",
        sector=SectorEmpresa.TECNOLOGIA,
        activo=True,
    )
    c2 = ClienteB2B(
        nombre_empresa="Métricas Admin Turismo",
        ruc="RUC-MET-TUR",
        email_contacto="met-tur@ejemplo.local",
        sector=SectorEmpresa.TURISMO,
        activo=True,
    )
    db.add_all([c1, c2])
    db.flush()

    cuenta1 = Cuenta(
        nombre_usuario="metricas admin tecnologia",
        password_hash="hash-de-prueba",
        rol=RolCuenta.EMPRESA,
        cliente_id=c1.id,
        activo=True,
    )
    cuenta2 = Cuenta(
        nombre_usuario="metricas admin turismo",
        password_hash="hash-de-prueba",
        rol=RolCuenta.EMPRESA,
        cliente_id=c2.id,
        activo=True,
    )
    db.add_all([cuenta1, cuenta2])
    db.flush()
    db.add_all(
        [
            Sesion(
                cuenta_id=cuenta1.id,
                token_hash="met-hash-en-linea",
                creada_en=ahora,
                ultima_actividad=ahora - timedelta(minutes=3),
                expira_en=ahora + timedelta(hours=1),
                revocada=False,
            ),
            Sesion(
                cuenta_id=cuenta2.id,
                token_hash="met-hash-inactiva",
                creada_en=ahora - timedelta(hours=2),
                ultima_actividad=ahora - timedelta(hours=1),
                expira_en=ahora + timedelta(hours=1),
                revocada=False,
            ),
            Sesion(
                cuenta_id=cuenta2.id,
                token_hash="met-hash-revocada",
                creada_en=ahora,
                ultima_actividad=ahora,
                expira_en=ahora + timedelta(hours=1),
                revocada=True,
            ),
        ]
    )

    cat1 = Categoria(
        nombre="Cat Métricas Tech", sector=SectorEmpresa.TECNOLOGIA
    )
    cat2 = Categoria(nombre="Cat Métricas Tur", sector=SectorEmpresa.TURISMO)
    p1 = Producto(
        categoria=cat1,
        nombre="Prod Métricas Uno",
        sku="SKU-MET-1",
        precio_caja=Decimal("10.00"),
        precio_unidad=Decimal("1.00"),
        unidades_por_caja=10,
    )
    p2 = Producto(
        categoria=cat2,
        nombre="Prod Métricas Dos",
        sku="SKU-MET-2",
        precio_caja=Decimal("20.00"),
        precio_unidad=Decimal("2.00"),
        unidades_por_caja=10,
    )
    p3 = Producto(
        categoria=cat1,
        nombre="Prod Métricas Sin Ventas",
        sku="SKU-MET-3",
        precio_caja=Decimal("30.00"),
        precio_unidad=Decimal("3.00"),
        unidades_por_caja=10,
        estado_activo=True,
    )
    db.add_all([cat1, cat2, p1, p2, p3])
    db.flush()
    db.add_all(
        [
            Inventario(
                producto_id=p1.id,
                existencias=Decimal("1.00"),
                stock_minimo=Decimal("5.00"),
            ),
            Inventario(
                producto_id=p2.id,
                existencias=Decimal("10.00"),
                stock_minimo=Decimal("0.00"),
            ),
        ]
    )

    def factura(serie, cliente, total, categoria, fecha, estado, en_revision=False):
        item = Factura(
            numero_serie=serie,
            codigo_verificacion=f"COD{serie[-8:]}",
            fecha=fecha,
            cliente_id=cliente.id,
            cliente_nombre=cliente.nombre_empresa,
            cliente_ruc=cliente.ruc,
            condicion_pago=CondicionPago.CONTADO,
            subtotal=total,
            base_gravada=Decimal("0.00"),
            base_exenta=total,
            itbms=Decimal("0.00"),
            portes=Decimal("0.00"),
            total=total,
            estado=estado,
            en_revision=en_revision,
            fecha_creacion=ahora,
            fecha_anulacion=ahora if estado == EstadoFactura.ANULADA else None,
        )
        item.lineas.append(
            LineaFactura(
                orden=1,
                descripcion=f"Línea {serie}",
                categoria=categoria,
                cantidad=Decimal("1.00"),
                precio_unitario=total,
                descuento_pct=Decimal("0.00"),
                gravada=False,
                unidades_por_caja=1,
                cobrar_por=CobrarPor.UNIDAD,
                monto=total,
            )
        )
        db.add(item)
        return item

    factura("FAC-MET-0001", c1, Decimal("100.00"), cat1.nombre, hoy, EstadoFactura.EMITIDA)
    factura(
        "FAC-MET-0002", c2, Decimal("50.00"), cat2.nombre, hoy, EstadoFactura.EN_REVISION
    )
    factura(
        "FAC-MET-0003",
        c2,
        Decimal("25.00"),
        cat2.nombre,
        hoy,
        EstadoFactura.EMITIDA,
        en_revision=True,
    )
    factura(
        "FAC-MET-0004", c1, Decimal("999.00"), cat1.nombre, hoy, EstadoFactura.ANULADA
    )
    factura(
        "FAC-MET-0005", c2, Decimal("500.00"), cat2.nombre, anterior_mes, EstadoFactura.EMITIDA
    )
    db.flush()

    def pedido(serie, estado, fecha, lineas):
        item = PedidoB2B(
            cliente_id=c1.id,
            estado=estado,
            total_estimado=sum((linea[3] for linea in lineas), Decimal("0.00")),
            notas=serie,
            fecha_creacion=fecha,
        )
        db.add(item)
        db.flush()
        for orden, (producto, cantidad, presentacion, subtotal) in enumerate(lineas, 1):
            db.add(
                LineaPedidoB2B(
                    pedido_id=item.id,
                    producto_id=producto.id,
                    tipo_empaque=presentacion,
                    cantidad=cantidad,
                    subtotal=subtotal,
                    orden=orden,
                )
            )
        db.flush()
        return item

    pedido(
        "PED-MET-1",
        EstadoPedido.PENDIENTE,
        ahora,
        [
            (p1, Decimal("2.00"), TipoEmpaque.CAJA, Decimal("40.00")),
            (p2, Decimal("5.00"), TipoEmpaque.UNIDAD, Decimal("25.00")),
        ],
    )
    pedido(
        "PED-MET-2",
        EstadoPedido.PROCESANDO,
        ahora,
        [
            (p1, Decimal("3.00"), TipoEmpaque.UNIDAD, Decimal("15.00")),
            (p2, Decimal("1.00"), TipoEmpaque.CAJA, Decimal("50.00")),
        ],
    )
    pedido(
        "PED-MET-CANCELADO",
        EstadoPedido.CANCELADO,
        ahora,
        [(p3, Decimal("100.00"), TipoEmpaque.CAJA, Decimal("999.00"))],
    )
    pedido(
        "PED-MET-ANTIGUO",
        EstadoPedido.PENDIENTE,
        datetime.combine(anterior_mes, datetime.min.time()).replace(tzinfo=timezone.utc),
        [(p3, Decimal("100.00"), TipoEmpaque.CAJA, Decimal("999.00"))],
    )
    db.flush()
    return c1, c2, p1, p2, p3


def test_admin_panel_resumen_con_datos_conocidos(client, db: Session):
    _sembrar(db)
    respuesta = client.get("/api/v1/admin/panel/resumen")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["empresas_total"] == 2
    assert datos["empresas_activas"] == 2
    assert datos["empresas_en_linea"] == 1
    assert datos["pedidos_por_facturar"] == 3
    assert datos["facturas_en_revision"] == 2
    assert datos["productos_bajo_minimo"] == 1
    assert _d(datos["ingresos_periodo"]) == Decimal("175.00")
    assert datos["facturas_periodo"] == 3


def test_admin_panel_ingresos_por_mes_empresa_sector_y_categoria(client, db: Session):
    c1, c2, _p1, _p2, _p3 = _sembrar(db)
    respuesta = client.get("/api/v1/admin/panel/ingresos")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert len(datos["por_mes"]) == 12
    assert datos["por_mes"][-1]["mes"] == date.today().strftime("%Y-%m")
    assert _d(datos["por_mes"][-1]["ingresos"]) == Decimal("175.00")
    assert datos["por_mes"][-1]["facturas"] == 3

    por_empresa = {item["empresa_id"]: item for item in datos["por_empresa"]}
    assert _d(por_empresa[c1.id]["ingresos"]) == Decimal("100.00")
    assert _d(por_empresa[c2.id]["ingresos"]) == Decimal("75.00")
    assert all(item["nombre"] != "Otras" for item in datos["por_empresa"])

    por_sector = {item["nombre"]: item for item in datos["por_sector"]}
    assert _d(por_sector["tecnologia"]["ingresos"]) == Decimal("100.00")
    assert _d(por_sector["turismo"]["ingresos"]) == Decimal("75.00")
    assert "anulada" not in por_sector

    por_categoria = {item["nombre"]: item for item in datos["por_categoria"]}
    assert _d(por_categoria["Cat Métricas Tech"]["ingresos"]) == Decimal("100.00")
    assert _d(por_categoria["Cat Métricas Tur"]["ingresos"]) == Decimal("75.00")


def test_admin_panel_ranking_productos_incluye_ventas_cero(client, db: Session):
    _c1, _c2, p1, p2, p3 = _sembrar(db)
    respuesta = client.get("/api/v1/admin/panel/productos")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    por_unidades = [item["producto_id"] for item in datos["mas_pedidos_por_unidades"]]
    assert por_unidades == [p1.id, p2.id, p3.id]
    assert _d(datos["mas_pedidos_por_unidades"][0]["unidades"]) == Decimal("23.00")
    assert _d(datos["mas_pedidos_por_unidades"][1]["unidades"]) == Decimal("15.00")

    por_monto = datos["mas_pedidos_por_monto"]
    assert [item["producto_id"] for item in por_monto] == [p2.id, p1.id, p3.id]
    assert _d(por_monto[0]["monto"]) == Decimal("75.00")
    assert _d(por_monto[1]["monto"]) == Decimal("55.00")

    primero = datos["menos_pedidos"][0]
    assert primero["producto_id"] == p3.id
    assert _d(primero["unidades"]) == Decimal("0.00")
    assert _d(primero["monto"]) == Decimal("0.00")
    assert primero["pedidos"] == 0


def test_admin_panel_respeta_rango_de_fechas(client, db: Session):
    _sembrar(db)
    hoy = date.today()
    respuesta = client.get(
        "/api/v1/admin/panel/resumen",
        params={"desde": hoy.isoformat(), "hasta": hoy.isoformat()},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert _d(respuesta.json()["ingresos_periodo"]) == Decimal("175.00")

    anterior = hoy - timedelta(days=45)
    respuesta = client.get(
        "/api/v1/admin/panel/resumen",
        params={"desde": anterior.isoformat(), "hasta": anterior.isoformat()},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert _d(respuesta.json()["ingresos_periodo"]) == Decimal("0.00")
    assert respuesta.json()["facturas_periodo"] == 0
