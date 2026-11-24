from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.pedidos import (
    LineaPedido,
    Presentacion,
    armar_datos_factura,
    calcular_pedido,
    linea_pedido_desde_modelo,
    pedido_a_lineas_factura,
    precio_de_presentacion,
    precio_unitario,
    subtotal_linea,
    subtotal_pedido,
    validar_pedido_facturable,
)

PRECIOS = {
    Presentacion.CAJA: Decimal("24.00"),
    Presentacion.MEDIA_CAJA: Decimal("12.50"),
    Presentacion.UNIDAD: Decimal("1.10"),
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
    nombre="Galletas María",
    precio_caja=Decimal("24.00"),
    precio_media_caja=Decimal("12.50"),
    permite_media_caja=True,
    precio_unidad=Decimal("1.10"),
    unidades_por_caja=12,
    aplica_itbms=False,
)


# ---------- subtotales ----------

def test_subtotal_cajas():
    assert subtotal_linea(PRECIOS[Presentacion.CAJA], 3) == Decimal("72.00")


def test_subtotal_unidades_redondea():
    assert subtotal_linea(Decimal("1.105"), 1) == Decimal("1.11")


def test_subtotal_pedido_suma_lineas():
    lineas = [Decimal("72.00"), Decimal("12.50"), Decimal("2.20")]
    assert subtotal_pedido(lineas) == Decimal("86.70")


def test_precio_unitario_devuelve_el_precio_de_la_presentacion():
    assert precio_unitario(PRECIOS, Presentacion.MEDIA_CAJA) == Decimal("12.50")


def test_cantidad_cero_falla():
    with pytest.raises(ValueError):
        subtotal_linea(Decimal("1.00"), 0)


def test_presentacion_sin_precio_falla():
    with pytest.raises(ValueError):
        precio_unitario({Presentacion.CAJA: Decimal("24.00")}, Presentacion.UNIDAD)


# ---------- validaciones de línea ----------

def test_linea_con_precio_float_falla():
    with pytest.raises(TypeError):
        LineaPedido("Galletas", Presentacion.CAJA, 1, 24.0)


def test_linea_con_precio_negativo_falla():
    with pytest.raises(ValueError):
        LineaPedido("Galletas", Presentacion.CAJA, 1, Decimal("-1.00"))


def test_linea_con_cantidad_cero_falla():
    with pytest.raises(ValueError):
        LineaPedido("Galletas", Presentacion.CAJA, 0, Decimal("24.00"))


def test_linea_con_unidades_por_caja_cero_falla():
    with pytest.raises(ValueError):
        LineaPedido(
            "Galletas", Presentacion.CAJA, 1, Decimal("24.00"), unidades_por_caja=0
        )


def test_linea_con_descuento_mayor_a_100_falla():
    with pytest.raises(ValueError):
        LineaPedido(
            "Galletas", Presentacion.CAJA, 1, Decimal("24.00"),
            descuento_pct=Decimal("100.01"),
        )


# ---------- resumen de pedido ----------

def test_calcular_pedido_resume_lineas():
    lineas = [
        LineaPedido("Galletas", Presentacion.CAJA, 3, Decimal("24.00")),
        LineaPedido("Galletas", Presentacion.UNIDAD, 2, Decimal("1.10")),
    ]
    resumen = calcular_pedido(lineas)
    assert resumen.subtotales_lineas == [Decimal("72.00"), Decimal("2.20")]
    assert resumen.subtotal == Decimal("74.20")


def test_calcular_pedido_sin_lineas_falla():
    with pytest.raises(ValueError):
        calcular_pedido([])


# ---------- conversión a líneas de factura ----------

def test_pedido_a_lineas_factura_convierte_cada_linea():
    lineas = [
        LineaPedido(
            "Galletas", Presentacion.CAJA, 3, Decimal("24.00"), unidades_por_caja=12
        ),
        LineaPedido("Galletas", Presentacion.UNIDAD, 2, Decimal("1.10"), gravada=False),
    ]
    resultado = pedido_a_lineas_factura(lineas)
    assert len(resultado) == 2
    assert resultado[0].cantidad == Decimal("3")
    assert resultado[0].cobrar_por == "caja"
    assert resultado[0].unidades_por_caja == 12
    assert resultado[1].cobrar_por == "unidad"
    assert resultado[1].gravada is False


def test_media_caja_pendiente_de_definir():
    lineas = [LineaPedido("Galletas", Presentacion.MEDIA_CAJA, 1, Decimal("12.50"))]
    with pytest.raises(NotImplementedError):
        pedido_a_lineas_factura(lineas)


def test_pedido_sin_lineas_falla():
    with pytest.raises(ValueError):
        pedido_a_lineas_factura([])


# ---------- precios y líneas desde el modelo ----------

def test_precio_de_presentacion_caja_y_unidad():
    assert precio_de_presentacion(PRODUCTO, Presentacion.CAJA) == Decimal("24.00")
    assert precio_de_presentacion(PRODUCTO, Presentacion.UNIDAD) == Decimal("1.10")


def test_precio_media_caja_permitida():
    assert precio_de_presentacion(PRODUCTO, Presentacion.MEDIA_CAJA) == Decimal("12.50")


def test_media_caja_no_permitida_falla():
    producto = SimpleNamespace(**{**PRODUCTO.__dict__, "permite_media_caja": False})
    with pytest.raises(ValueError):
        precio_de_presentacion(producto, Presentacion.MEDIA_CAJA)


def test_media_caja_sin_precio_falla():
    producto = SimpleNamespace(**{**PRODUCTO.__dict__, "precio_media_caja": None})
    with pytest.raises(ValueError):
        precio_de_presentacion(producto, Presentacion.MEDIA_CAJA)


def test_linea_desde_modelo_copia_datos_del_producto():
    linea_modelo = SimpleNamespace(tipo_empaque="caja", cantidad=Decimal("3.00"))
    linea = linea_pedido_desde_modelo(linea_modelo, PRODUCTO)
    assert linea.descripcion == "Galletas María"
    assert linea.presentacion == Presentacion.CAJA
    assert linea.precio == Decimal("24.00")
    assert linea.unidades_por_caja == 12
    assert linea.gravada is False
    assert linea.producto_id == 7
    assert linea.subtotal == Decimal("72.00")


def test_linea_desde_modelo_acepta_enum_con_value():
    linea_modelo = SimpleNamespace(
        tipo_empaque=SimpleNamespace(value="unidad"), cantidad=Decimal("2.00")
    )
    linea = linea_pedido_desde_modelo(linea_modelo, PRODUCTO)
    assert linea.presentacion == Presentacion.UNIDAD
    assert linea.precio == Decimal("1.10")


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
        CLIENTE, TOTALES, "FAC-2026-0001", "ABC123", date(2026, 11, 24)
    )
    assert datos["cliente_nombre"] == "Distribuidora Sol"
    assert datos["cliente_correo"] == "compras@sol.com"
    assert datos["total"] == Decimal("107.00")
    assert datos["numero_serie"] == "FAC-2026-0001"


def test_direccion_larga_se_recorta():
    cliente = SimpleNamespace(
        nombre_empresa="X", ruc="1", email_contacto="a@b.com",
        telefono=None, direccion="a" * 400,
    )
    datos = armar_datos_factura(
        cliente, TOTALES, "FAC-2026-0001", "ABC123", date(2026, 11, 24)
    )
    assert len(datos["cliente_direccion"]) == 250


def test_totales_incompletos_fallan():
    with pytest.raises(ValueError):
        armar_datos_factura(
            CLIENTE, {"total": Decimal("1.00")}, "FAC-2026-0001", "ABC123",
            date(2026, 11, 24),
        )


def test_codigo_verificacion_demasiado_largo_falla():
    with pytest.raises(ValueError):
        armar_datos_factura(
            CLIENTE, TOTALES, "FAC-2026-0001", "X" * 13, date(2026, 11, 24)
        )