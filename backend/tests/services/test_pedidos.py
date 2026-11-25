from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.catalogo import (
    Categoria,
    ClienteB2B,
    EstadoPedido,
    TipoEmpaque,
    LineaPedidoB2B,
    PedidoB2B,
    Producto,
)
from app.models.facturacion import Factura
from app.services.pedidos import (
    LineaPedido,
    armar_datos_factura,
    calcular_pedido,
    facturar_pedido_b2b,
    linea_pedido_desde_modelo,
    pedido_a_lineas_factura,
    precio_de_presentacion,
    precio_unitario,
    subtotal_linea,
    subtotal_pedido,
    validar_pedido_facturable,
)


PRECIOS = {
    TipoEmpaque.CAJA: Decimal("24.00"),
    TipoEmpaque.MEDIA_CAJA: Decimal("12.50"),
    TipoEmpaque.UNIDAD: Decimal("1.10"),
}

CLIENTE = SimpleNamespace(
    nombre_empresa="Distribuidora Sol",
    ruc="123-456-789",
    email_contacto="compras@sol.com",
    telefono="6000-0000",
    direccion="Calle 1",
)

TOTALES = {
    "subtotal": Decimal("100.00"),
    "descuento_total": Decimal("0.00"),
    "base_gravada": Decimal("100.00"),
    "base_exenta": Decimal("0.00"),
    "itbms": Decimal("7.00"),
    "total": Decimal("107.00"),
}

PRODUCTO = SimpleNamespace(
    id=7,
    nombre="Galletas MarÃ­a",
    precio_caja=Decimal("24.00"),
    precio_media_caja=Decimal("12.50"),
    permite_media_caja=True,
    precio_unidad=Decimal("1.10"),
    unidades_por_caja=12,
    aplica_itbms=False,
)


# ---------- subtotales ----------

def test_subtotal_cajas():
    assert subtotal_linea(PRECIOS[TipoEmpaque.CAJA], 3) == Decimal("72.00")


def test_subtotal_unidades_redondea():
    assert subtotal_linea(Decimal("1.105"), 1) == Decimal("1.11")


def test_subtotal_pedido_suma_lineas():
    lineas = [Decimal("72.00"), Decimal("12.50"), Decimal("2.20")]
    assert subtotal_pedido(lineas) == Decimal("86.70")


def test_precio_unitario_devuelve_el_precio_de_la_presentacion():
    assert precio_unitario(PRECIOS, TipoEmpaque.MEDIA_CAJA) == Decimal("12.50")


def test_cantidad_cero_falla():
    with pytest.raises(ValueError):
        subtotal_linea(Decimal("1.00"), 0)


def test_presentacion_sin_precio_falla():
    with pytest.raises(ValueError):
        precio_unitario(
            {TipoEmpaque.CAJA: Decimal("24.00")},
            TipoEmpaque.UNIDAD,
        )


# ---------- validaciones de lÃ­nea ----------

def test_linea_con_precio_float_falla():
    with pytest.raises(TypeError):
        LineaPedido("Galletas", TipoEmpaque.CAJA, 1, 24.0)


def test_linea_con_precio_negativo_falla():
    with pytest.raises(ValueError):
        LineaPedido(
            "Galletas",
            TipoEmpaque.CAJA,
            1,
            Decimal("-1.00"),
        )


def test_linea_con_cantidad_cero_falla():
    with pytest.raises(ValueError):
        LineaPedido(
            "Galletas",
            TipoEmpaque.CAJA,
            0,
            Decimal("24.00"),
        )


def test_linea_con_unidades_por_caja_cero_falla():
    with pytest.raises(ValueError):
        LineaPedido(
            "Galletas",
            TipoEmpaque.CAJA,
            1,
            Decimal("24.00"),
            unidades_por_caja=0,
        )


def test_linea_con_descuento_mayor_a_100_falla():
    with pytest.raises(ValueError):
        LineaPedido(
            "Galletas",
            TipoEmpaque.CAJA,
            1,
            Decimal("24.00"),
            descuento_pct=Decimal("100.01"),
        )


# ---------- resumen de pedido ----------

def test_calcular_pedido_resume_lineas():
    lineas = [
        LineaPedido(
            "Galletas",
            TipoEmpaque.CAJA,
            3,
            Decimal("24.00"),
        ),
        LineaPedido(
            "Galletas",
            TipoEmpaque.UNIDAD,
            2,
            Decimal("1.10"),
        ),
    ]

    resumen = calcular_pedido(lineas)

    assert resumen.subtotales_lineas == [
        Decimal("72.00"),
        Decimal("2.20"),
    ]
    assert resumen.subtotal == Decimal("74.20")


def test_calcular_pedido_sin_lineas_falla():
    with pytest.raises(ValueError):
        calcular_pedido([])


# ---------- conversiÃ³n a lÃ­neas de factura ----------

def test_pedido_a_lineas_factura_convierte_cada_linea():
    lineas = [
        LineaPedido(
            "Galletas",
            TipoEmpaque.CAJA,
            3,
            Decimal("24.00"),
            unidades_por_caja=12,
        ),
        LineaPedido(
            "Galletas",
            TipoEmpaque.UNIDAD,
            2,
            Decimal("1.10"),
            gravada=False,
        ),
    ]

    resultado = pedido_a_lineas_factura(lineas)

    assert len(resultado) == 2
    assert resultado[0].cantidad == Decimal("3")
    assert resultado[0].cobrar_por == "caja"
    assert resultado[0].unidades_por_caja == 12
    assert resultado[1].cobrar_por == "unidad"
    assert resultado[1].gravada is False


def test_media_caja_se_convierte_a_linea_facturable():
    lineas = [
        LineaPedido(
            "Galletas",
            TipoEmpaque.MEDIA_CAJA,
            1,
            Decimal("12.50"),
            unidades_por_caja=12,
        )
    ]

    resultado = pedido_a_lineas_factura(lineas)

    assert len(resultado) == 1
    assert resultado[0].cantidad == Decimal("1")
    assert resultado[0].cobrar_por == "unidad"
    assert resultado[0].precio_unitario == Decimal("12.50")
    assert resultado[0].precio_unidad is None


def test_pedido_sin_lineas_falla():
    with pytest.raises(ValueError):
        pedido_a_lineas_factura([])


# ---------- precios y lÃ­neas desde el modelo ----------

def test_precio_de_presentacion_caja_y_unidad():
    assert precio_de_presentacion(
        PRODUCTO,
        TipoEmpaque.CAJA,
    ) == Decimal("24.00")

    assert precio_de_presentacion(
        PRODUCTO,
        TipoEmpaque.UNIDAD,
    ) == Decimal("1.10")


def test_precio_media_caja_permitida():
    assert precio_de_presentacion(
        PRODUCTO,
        TipoEmpaque.MEDIA_CAJA,
    ) == Decimal("12.50")


def test_media_caja_no_permitida_falla():
    producto = SimpleNamespace(
        **{**PRODUCTO.__dict__, "permite_media_caja": False}
    )

    with pytest.raises(ValueError):
        precio_de_presentacion(producto, TipoEmpaque.MEDIA_CAJA)


def test_media_caja_sin_precio_falla():
    producto = SimpleNamespace(
        **{**PRODUCTO.__dict__, "precio_media_caja": None}
    )

    with pytest.raises(ValueError):
        precio_de_presentacion(producto, TipoEmpaque.MEDIA_CAJA)


def test_linea_desde_modelo_copia_datos_del_producto():
    linea_modelo = SimpleNamespace(
        tipo_empaque="caja",
        cantidad=Decimal("3.00"),
    )

    linea = linea_pedido_desde_modelo(linea_modelo, PRODUCTO)

    assert linea.descripcion == "Galletas MarÃ­a"
    assert linea.presentacion == TipoEmpaque.CAJA
    assert linea.precio == Decimal("24.00")
    assert linea.unidades_por_caja == 12
    assert linea.gravada is False
    assert linea.producto_id == 7
    assert linea.subtotal == Decimal("72.00")


def test_linea_desde_modelo_acepta_enum_con_value():
    linea_modelo = SimpleNamespace(
        tipo_empaque=SimpleNamespace(value="unidad"),
        cantidad=Decimal("2.00"),
    )

    linea = linea_pedido_desde_modelo(linea_modelo, PRODUCTO)

    assert linea.presentacion == TipoEmpaque.UNIDAD
    assert linea.precio == Decimal("1.10")


def test_linea_media_caja_desde_modelo_usa_precio_especial():
    linea_modelo = SimpleNamespace(
        tipo_empaque="media_caja",
        cantidad=Decimal("1.00"),
    )

    linea = linea_pedido_desde_modelo(linea_modelo, PRODUCTO)

    assert linea.presentacion == TipoEmpaque.MEDIA_CAJA
    assert linea.precio == Decimal("12.50")
    assert linea.precio_unidad is None


# ---------- estado del pedido ----------

def test_pedido_pendiente_se_puede_facturar():
    validar_pedido_facturable("pendiente", None)


def test_pedido_facturado_falla():
    with pytest.raises(ValueError):
        validar_pedido_facturable("facturado", None)


def test_pedido_con_factura_generada_falla():
    with pytest.raises(ValueError):
        validar_pedido_facturable("procesando", 15)


def test_pedido_cancelado_falla():
    with pytest.raises(ValueError):
        validar_pedido_facturable("cancelado", None)


# ---------- datos de la factura ----------

def test_armar_datos_factura_copia_cliente_y_totales():
    datos = armar_datos_factura(
        CLIENTE,
        TOTALES,
        "FAC-2026-0001",
        "ABC123",
        date(2026, 11, 24),
    )

    assert datos["cliente_nombre"] == "Distribuidora Sol"
    assert datos["cliente_correo"] == "compras@sol.com"
    assert datos["total"] == Decimal("107.00")
    assert datos["numero_serie"] == "FAC-2026-0001"


def test_direccion_larga_se_recorta():
    cliente = SimpleNamespace(
        nombre_empresa="X",
        ruc="1",
        email_contacto="a@b.com",
        telefono=None,
        direccion="a" * 400,
    )

    datos = armar_datos_factura(
        cliente,
        TOTALES,
        "FAC-2026-0001",
        "ABC123",
        date(2026, 11, 24),
    )

    assert len(datos["cliente_direccion"]) == 250


def test_totales_incompletos_fallan():
    with pytest.raises(ValueError):
        armar_datos_factura(
            CLIENTE,
            {"total": Decimal("1.00")},
            "FAC-2026-0001",
            "ABC123",
            date(2026, 11, 24),
        )


def test_codigo_verificacion_demasiado_largo_falla():
    with pytest.raises(ValueError):
        armar_datos_factura(
            CLIENTE,
            TOTALES,
            "FAC-2026-0001",
            "X" * 13,
            date(2026, 11, 24),
        )


# ---------- ciclo completo de facturaciÃ³n B2B ----------

@pytest.fixture
def db():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)

    with Session(motor) as sesion:
        yield sesion

    motor.dispose()


@pytest.fixture
def pedido_b2b(db):
    categoria = Categoria(nombre="Alimentos")

    cliente = ClienteB2B(
        nombre_empresa="Distribuidora Sol",
        ruc="123-456-789",
        email_contacto="compras@sol.com",
        telefono="6000-0000",
        direccion="Calle 1",
    )

    producto = Producto(
        categoria=categoria,
        nombre="Galletas MarÃ­a",
        sku="GAL-001",
        precio_caja=Decimal("24.00"),
        precio_unidad=Decimal("1.10"),
        precio_media_caja=Decimal("12.50"),
        permite_media_caja=True,
        unidades_por_caja=12,
        aplica_itbms=True,
    )

    pedido = PedidoB2B(
        cliente=cliente,
        estado=EstadoPedido.PENDIENTE,
        notas="Pedido de prueba",
    )

    pedido.lineas.append(
        LineaPedidoB2B(
            producto=producto,
            tipo_empaque=TipoEmpaque.CAJA,
            cantidad=Decimal("2.00"),
            subtotal=Decimal("48.00"),
            orden=1,
        )
    )

    db.add(pedido)
    db.flush()

    return pedido


def preparar_facturacion(monkeypatch):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")

    monkeypatch.setattr(
        "app.services.pedidos.ContadorSerieRepository.obtener_siguiente_numero",
        staticmethod(lambda db, anio: f"FAC-{anio}-0001"),
    )


def test_facturar_pedido_b2b_crea_factura_y_actualiza_pedido(
    db, pedido_b2b, monkeypatch
):
    preparar_facturacion(monkeypatch)

    factura = facturar_pedido_b2b(db, pedido_b2b.id)

    assert factura.id is not None
    assert factura.numero_serie.startswith("FAC-")
    assert factura.codigo_verificacion
    assert factura.cliente_nombre == "Distribuidora Sol"

    assert factura.subtotal == Decimal("48.00")
    assert factura.base_gravada == Decimal("48.00")
    assert factura.itbms == Decimal("3.36")
    assert factura.total == Decimal("51.36")

    assert len(factura.lineas) == 1
    assert factura.lineas[0].descripcion == "Galletas MarÃ­a"
    assert factura.lineas[0].cantidad == Decimal("2.00")
    assert factura.lineas[0].precio_unitario == Decimal("24.00")
    assert factura.lineas[0].monto == Decimal("48.00")

    assert pedido_b2b.estado == EstadoPedido.FACTURADO
    assert pedido_b2b.factura_generada_id == factura.id


def test_facturar_pedido_b2b_convierte_media_caja(
    db, pedido_b2b, monkeypatch
):
    preparar_facturacion(monkeypatch)

    linea = pedido_b2b.lineas[0]
    linea.tipo_empaque = TipoEmpaque.MEDIA_CAJA
    linea.cantidad = Decimal("2.00")
    linea.subtotal = Decimal("25.00")

    factura = facturar_pedido_b2b(db, pedido_b2b.id)

    assert len(factura.lineas) == 1

    linea_factura = factura.lineas[0]

    assert linea_factura.descripcion == "Media caja - Galletas MarÃ­a"
    assert linea_factura.cantidad == Decimal("2.00")
    assert linea_factura.precio_unitario == Decimal("12.50")
    assert linea_factura.precio_unidad is None
    assert linea_factura.cobrar_por.value == "unidad"
    assert linea_factura.monto == Decimal("25.00")


def test_facturar_pedido_cancelado_falla(db, pedido_b2b, monkeypatch):
    preparar_facturacion(monkeypatch)

    pedido_b2b.estado = EstadoPedido.CANCELADO
    db.flush()

    with pytest.raises(ValueError, match="cancelado"):
        facturar_pedido_b2b(db, pedido_b2b.id)


def test_facturar_pedido_ya_facturado_falla(db, pedido_b2b, monkeypatch):
    preparar_facturacion(monkeypatch)

    pedido_b2b.estado = EstadoPedido.FACTURADO
    db.flush()

    with pytest.raises(ValueError, match="ya fue facturado"):
        facturar_pedido_b2b(db, pedido_b2b.id)


def test_facturar_pedido_inexistente_falla(db):
    with pytest.raises(ValueError, match="No existe el pedido"):
        facturar_pedido_b2b(db, 9999)


def test_facturar_pedido_sin_lineas_falla(db, pedido_b2b, monkeypatch):
    preparar_facturacion(monkeypatch)

    pedido_b2b.lineas.clear()
    db.flush()

    with pytest.raises(ValueError, match="no tiene lÃ­neas"):
        facturar_pedido_b2b(db, pedido_b2b.id)


def test_facturar_pedido_b2b_no_hace_commit_y_permite_rollback(
    db, pedido_b2b, monkeypatch
):
    preparar_facturacion(monkeypatch)

    pedido_id = pedido_b2b.id

    # Guardamos los datos iniciales antes de probar la facturaciÃ³n.
    db.commit()

    factura = facturar_pedido_b2b(db, pedido_id)

    assert factura.id is not None
    assert pedido_b2b.estado == EstadoPedido.FACTURADO

    db.rollback()

    pedido = db.scalar(
        select(PedidoB2B).where(PedidoB2B.id == pedido_id)
    )

    facturas = db.scalars(select(Factura)).all()

    assert pedido is not None
    assert pedido.estado == EstadoPedido.PENDIENTE
    assert pedido.factura_generada_id is None
    assert facturas == []