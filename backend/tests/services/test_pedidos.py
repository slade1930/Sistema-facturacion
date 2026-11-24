from decimal import Decimal

import pytest

from app.services.pedidos import (
    LineaPedido,
    Presentacion,
    calcular_pedido,
    pedido_a_lineas_factura,
    precio_unitario,
    subtotal_linea,
    subtotal_pedido,
)

PRECIOS = {
    Presentacion.CAJA: Decimal("24.00"),
    Presentacion.MEDIA_CAJA: Decimal("12.50"),
    Presentacion.UNIDAD: Decimal("1.10"),
}


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


def test_linea_con_precio_float_falla():
    with pytest.raises(TypeError):
        LineaPedido("Galletas", Presentacion.CAJA, 1, 24.0)


def test_linea_con_precio_negativo_falla():
    with pytest.raises(ValueError):
        LineaPedido("Galletas", Presentacion.CAJA, 1, Decimal("-1.00"))


def test_linea_con_cantidad_cero_falla():
    with pytest.raises(ValueError):
        LineaPedido("Galletas", Presentacion.CAJA, 0, Decimal("24.00"))


def test_calcular_pedido_resume_lineas():
    lineas = [
        LineaPedido("Galletas", Presentacion.CAJA, 3, Decimal("24.00")),
        LineaPedido("Galletas", Presentacion.UNIDAD, 2, Decimal("1.10")),
    ]
    resumen = calcular_pedido(lineas)
    assert resumen.subtotales_lineas == [Decimal("72.00"), Decimal("2.20")]
    assert resumen.subtotal == Decimal("74.20")


def test_pedido_a_lineas_factura_convierte_cada_linea():
    lineas = [
        LineaPedido("Galletas", Presentacion.CAJA, 3, Decimal("24.00")),
        LineaPedido("Galletas", Presentacion.UNIDAD, 2, Decimal("1.10")),
    ]
    resultado = pedido_a_lineas_factura(lineas)
    assert len(resultado) == 2
    assert resultado[0].subtotal == Decimal("72.00")
    assert resultado[1].descripcion == "Galletas (unidad)"


def test_pedido_sin_lineas_falla():
    with pytest.raises(ValueError):
        pedido_a_lineas_factura([])