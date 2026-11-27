"""Pruebas unitarias de app.services.totales (sin base de datos)."""

from decimal import Decimal

import pytest

from app.models.facturacion import Factura, LineaFactura
from app.services.totales import (
    TASA_ITBMS,
    aplicar_totales,
    calcular_bruto_linea,
    calcular_monto_linea,
    calcular_totales,
)


def _linea(**kwargs):
    """Línea como dict, con los defaults del esquema oficial."""
    base = {
        "cantidad": Decimal("1"),
        "precio_unitario": Decimal("0.00"),
        "descuento_pct": Decimal("0.00"),
        "gravada": True,
        "cobrar_por": "unidad",
        "unidades_por_caja": 1,
    }
    base.update(kwargs)
    return base


class TestCalcularMontoLinea:
    def test_cantidad_por_precio(self):
        linea = _linea(cantidad=Decimal("2"), precio_unitario=Decimal("10.50"))
        assert calcular_monto_linea(linea) == Decimal("21.00")

    def test_descuento_porcentaje(self):
        linea = _linea(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            descuento_pct=Decimal("10.00"),
        )
        assert calcular_monto_linea(linea) == Decimal("90.00")

    def test_redondeo_half_up_en_linea(self):
        # 1 x 0.335 = 0.335 -> 0.34 con ROUND_HALF_UP (no 0.33 del banker)
        linea = _linea(cantidad=Decimal("1"), precio_unitario=Decimal("0.335"))
        assert calcular_monto_linea(linea) == Decimal("0.34")

    def test_acepta_objeto_orm(self):
        linea = LineaFactura(
            orden=1,
            descripcion="Producto de prueba",
            cantidad=Decimal("3"),
            precio_unitario=Decimal("4.00"),
            descuento_pct=Decimal("0"),
            gravada=True,
            unidades_por_caja=1,
        )
        assert calcular_monto_linea(linea) == Decimal("12.00")

    def test_campos_faltantes_lanzan_error(self):
        with pytest.raises(ValueError):
            calcular_monto_linea({"precio_unitario": Decimal("1.00")})
        with pytest.raises(ValueError):
            calcular_monto_linea({"cantidad": Decimal("1")})

    def test_cantidad_menor_a_0_01_lanza_error(self):
        # ck_linea_factura_cantidad del esquema oficial
        linea = _linea(cantidad=Decimal("0.001"), precio_unitario=Decimal("1.00"))
        with pytest.raises(ValueError):
            calcular_monto_linea(linea)

    def test_precio_negativo_lanza_error(self):
        linea = _linea(precio_unitario=Decimal("-0.01"))
        with pytest.raises(ValueError):
            calcular_monto_linea(linea)

    def test_descuento_fuera_de_rango_lanza_error(self):
        with pytest.raises(ValueError):
            calcular_monto_linea(_linea(descuento_pct=Decimal("100.01")))
        with pytest.raises(ValueError):
            calcular_monto_linea(_linea(descuento_pct=Decimal("-0.01")))

    def test_descuento_100_porciento_deja_monto_cero(self):
        linea = _linea(
            cantidad=Decimal("2"),
            precio_unitario=Decimal("10.00"),
            descuento_pct=Decimal("100.00"),
        )
        assert calcular_monto_linea(linea) == Decimal("0.00")

    def test_bruto_no_descuenta(self):
        linea = _linea(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("80.00"),
            descuento_pct=Decimal("25.00"),
        )
        assert calcular_bruto_linea(linea) == Decimal("80.00")
        assert calcular_monto_linea(linea) == Decimal("60.00")


class TestCalcularTotales:
    def test_una_linea_gravada(self):
        lineas = [_linea(cantidad=Decimal("2"), precio_unitario=Decimal("10.00"))]
        t = calcular_totales(lineas)
        assert t["subtotal"] == Decimal("20.00")
        assert t["descuento_total"] == Decimal("0.00")
        assert t["base_gravada"] == Decimal("20.00")
        assert t["base_exenta"] == Decimal("0.00")
        assert t["itbms"] == Decimal("1.40")  # 20 * 0.07
        assert t["total"] == Decimal("21.40")

    def test_linea_exenta_no_genera_itbms(self):
        lineas = [_linea(precio_unitario=Decimal("50.00"), gravada=False)]
        t = calcular_totales(lineas)
        assert t["base_exenta"] == Decimal("50.00")
        assert t["base_gravada"] == Decimal("0.00")
        assert t["itbms"] == Decimal("0.00")
        assert t["total"] == Decimal("50.00")

    def test_mixto_gravada_y_exenta(self):
        lineas = [
            _linea(precio_unitario=Decimal("100.00"), gravada=True),
            _linea(precio_unitario=Decimal("40.00"), gravada=False),
        ]
        t = calcular_totales(lineas)
        assert t["subtotal"] == Decimal("140.00")
        assert t["base_gravada"] == Decimal("100.00")
        assert t["base_exenta"] == Decimal("40.00")
        assert t["itbms"] == Decimal("7.00")
        assert t["total"] == Decimal("147.00")

    def test_itbms_redondea_half_up(self):
        # base_gravada = 1.50 -> 1.50 * 0.07 = 0.105 -> 0.11 (no 0.10)
        lineas = [
            _linea(
                cantidad=Decimal("1.5"),
                precio_unitario=Decimal("1.00"),
                gravada=True,
            )
        ]
        t = calcular_totales(lineas)
        assert t["base_gravada"] == Decimal("1.50")
        assert t["itbms"] == Decimal("0.11")
        assert t["total"] == Decimal("1.61")

    def test_descuento_baja_base_gravada(self):
        lineas = [
            _linea(
                cantidad=Decimal("1"),
                precio_unitario=Decimal("200.00"),
                descuento_pct=Decimal("25.00"),
                gravada=True,
            )
        ]
        t = calcular_totales(lineas)
        # Con descuentos el subtotal muestra el bruto y el dto va aparte.
        assert t["subtotal"] == Decimal("200.00")
        assert t["descuento_total"] == Decimal("50.00")
        assert t["base_gravada"] == Decimal("150.00")
        assert t["itbms"] == Decimal("10.50")
        assert t["total"] == Decimal("160.50")

    def test_portes_suman_al_total_sin_itbms(self):
        # Regla asumida: portes no gravan ITBMS. Confirmar con el equipo.
        lineas = [_linea(precio_unitario=Decimal("10.00"), gravada=True)]
        t = calcular_totales(lineas, portes=Decimal("5.00"))
        assert t["itbms"] == Decimal("0.70")
        assert t["total"] == Decimal("15.70")

    def test_sin_lineas_todo_cero(self):
        t = calcular_totales([])
        for valor in t.values():
            assert valor == Decimal("0.00")

    def test_portes_negativo_lanza_error(self):
        with pytest.raises(ValueError):
            calcular_totales([], portes=Decimal("-1.00"))

    def test_sin_precio_unidad_caja_y_unidad_usan_el_mismo_precio(self):
        # Sin precio_unidad, las dos formas caen en precio_unitario.
        por_unidad = _linea(
            cantidad=Decimal("2"),
            precio_unitario=Decimal("10.00"),
            cobrar_por="unidad",
            unidades_por_caja=12,
        )
        por_caja = _linea(
            cantidad=Decimal("2"),
            precio_unitario=Decimal("10.00"),
            cobrar_por="caja",
            unidades_por_caja=12,
        )
        assert calcular_monto_linea(por_unidad) == calcular_monto_linea(por_caja)

    def test_tasa_itbms_es_7_porciento(self):
        assert TASA_ITBMS == Decimal("0.07")

    def test_gravada_none_cuenta_como_gravada(self):
        # El default del esquema es gravada=True; None no debe volverla exenta.
        lineas = [_linea(precio_unitario=Decimal("10.00"), gravada=None)]
        t = calcular_totales(lineas)
        assert t["base_gravada"] == Decimal("10.00")
        assert t["itbms"] == Decimal("0.70")

    def test_linea_exenta_con_descuento_va_a_base_exenta_neta(self):
        lineas = [
            _linea(
                precio_unitario=Decimal("100.00"),
                descuento_pct=Decimal("10.00"),
                gravada=False,
            )
        ]
        t = calcular_totales(lineas)
        assert t["subtotal"] == Decimal("100.00")
        assert t["base_exenta"] == Decimal("90.00")
        assert t["descuento_total"] == Decimal("10.00")
        assert t["itbms"] == Decimal("0.00")
        assert t["total"] == Decimal("90.00")

    def test_linea_gravada_precio_cero_no_genera_itbms(self):
        lineas = [_linea(precio_unitario=Decimal("0.00"), gravada=True)]
        t = calcular_totales(lineas)
        assert t["total"] == Decimal("0.00")


class TestAplicarTotales:
    def test_escribe_campos_en_factura_dict(self):
        factura = {
            "portes": Decimal("0.00"),
            "lineas": [_linea(precio_unitario=Decimal("10.00"))],
        }
        t = aplicar_totales(factura)
        assert factura["total"] == t["total"] == Decimal("10.70")
        assert factura["itbms"] == Decimal("0.70")

    def test_espacia_monto_en_lineas_sin_monto(self):
        linea = _linea(cantidad=Decimal("2"), precio_unitario=Decimal("5.00"))
        factura = {"portes": None, "lineas": [linea]}
        aplicar_totales(factura)
        assert linea["monto"] == Decimal("10.00")

    def test_no_pisa_monto_existente(self):
        linea = _linea(precio_unitario=Decimal("10.00"), monto=Decimal("999.00"))
        factura = {"portes": None, "lineas": [linea]}
        aplicar_totales(factura)
        assert linea["monto"] == Decimal("999.00")

    def test_funciona_con_objetos_orm_reales(self):
        # Sin base de datos: objetos transitorios de los modelos oficiales.
        l1 = LineaFactura(
            orden=1,
            descripcion="Gravado",
            cantidad=Decimal("2"),
            precio_unitario=Decimal("10.00"),
            descuento_pct=Decimal("0"),
            gravada=True,
        )
        l2 = LineaFactura(
            orden=2,
            descripcion="Exento",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("5.00"),
            descuento_pct=Decimal("0"),
            gravada=False,
        )
        factura = Factura(
            lineas=[l1, l2],
            portes=Decimal("1.00"),
        )
        t = aplicar_totales(factura)

        assert factura.subtotal == Decimal("25.00")
        assert factura.base_gravada == Decimal("20.00")
        assert factura.base_exenta == Decimal("5.00")
        assert factura.itbms == Decimal("1.40")
        assert factura.total == Decimal("27.40")  # 20 + 5 + 1.40 + portes 1.00
        assert l1.monto == Decimal("20.00")
        assert l2.monto == Decimal("5.00")
        assert t["total"] == factura.total


class TestReglaDeCalculo:
    """Gente, casos de la regla de cálculo para que no se nos mueva un centavo."""

    def test_uno_por_cero_cero_one_five_con_diez_porciento_da_cero_cero_one(self):
        linea = _linea(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("0.015"),
            descuento_pct=Decimal("10"),
        )
        assert calcular_monto_linea(linea) == Decimal("0.01")

    def test_siete_por_cero_cero_one_two_five_con_quince_porciento_da_cero_cero_four(self):
        linea = _linea(
            cantidad=Decimal("7"),
            precio_unitario=Decimal("0.125"),
            descuento_pct=Decimal("15"),
        )
        assert calcular_monto_linea(linea) == Decimal("0.74")

    def test_ocho_setenta_y_cinco_por_dos_con_tres_porciento(self):
        linea = _linea(
            cantidad=Decimal("8.75"),
            precio_unitario=Decimal("2"),
            descuento_pct=Decimal("3"),
        )
        assert calcular_monto_linea(linea) == Decimal("16.98")

    def test_diecinueve_cincuenta_con_cinco_porciento(self):
        linea = _linea(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("19.50"),
            descuento_pct=Decimal("5"),
        )
        assert calcular_monto_linea(linea) == Decimal("18.53")

    def test_redondeo_half_up_empuja_el_cinco_hacia_arriba(self):
        assert calcular_monto_linea(
            _linea(cantidad=Decimal("1"), precio_unitario=Decimal("0.005"))
        ) == Decimal("0.01")
        assert calcular_monto_linea(
            _linea(cantidad=Decimal("1"), precio_unitario=Decimal("2.345"))
        ) == Decimal("2.35")

    def test_descuento_de_cien_porciento_deja_cero(self):
        linea = _linea(
            cantidad=Decimal("10"),
            precio_unitario=Decimal("10"),
            descuento_pct=Decimal("100"),
        )
        assert calcular_monto_linea(linea) == Decimal("0.00")

    def test_lineas_gravadas_mezcladas_con_descuentos_distintos(self):
        lineas = [
            _linea(
                cantidad=Decimal("2"),
                precio_unitario=Decimal("8.75"),
                descuento_pct=Decimal("3"),
                gravada=True,
            ),
            _linea(
                cantidad=Decimal("1"),
                precio_unitario=Decimal("19.50"),
                descuento_pct=Decimal("5"),
                gravada=True,
            ),
        ]
        t = calcular_totales(lineas)
        assert t == {
            "subtotal": Decimal("37.00"),
            "descuento_total": Decimal("1.49"),
            "base_gravada": Decimal("35.51"),
            "base_exenta": Decimal("0.00"),
            "itbms": Decimal("2.49"),
            "total": Decimal("38.00"),
        }
        assert t["subtotal"] - t["descuento_total"] == (
            t["base_gravada"] + t["base_exenta"]
        )

    def test_linea_exenta_con_descuento_y_gravada_sin_descuento(self):
        lineas = [
            _linea(
                cantidad=Decimal("1"),
                precio_unitario=Decimal("100.00"),
                descuento_pct=Decimal("10"),
                gravada=False,
            ),
            _linea(
                cantidad=Decimal("1"),
                precio_unitario=Decimal("50.00"),
                gravada=True,
            ),
        ]
        t = calcular_totales(lineas)
        assert t["subtotal"] == Decimal("150.00")
        assert t["descuento_total"] == Decimal("10.00")
        assert t["base_exenta"] == Decimal("90.00")
        assert t["base_gravada"] == Decimal("50.00")
        assert t["itbms"] == Decimal("3.50")
        assert t["total"] == Decimal("143.50")

    def test_una_linea_por_caja_y_otra_por_unidad(self):
        lineas = [
            _linea(
                cantidad=Decimal("12"),
                precio_unitario=Decimal("30.00"),
                cobrar_por="unidad",
                unidades_por_caja=24,
            ),
            _linea(
                cantidad=Decimal("2"),
                precio_unitario=Decimal("30.00"),
                cobrar_por="caja",
                unidades_por_caja=24,
            ),
        ]
        t = calcular_totales(lineas)
        assert t["subtotal"] == Decimal("420.00")
        assert t["base_gravada"] == Decimal("420.00")
        assert t["itbms"] == Decimal("29.40")
        assert t["total"] == Decimal("449.40")

    def test_precio_unidad_directo_tiene_prioridad(self):
        por_unidad = _linea(
            cantidad=Decimal("5"),
            precio_unitario=Decimal("10.00"),
            precio_unidad=Decimal("2.50"),
        )
        por_caja = {**por_unidad, "cobrar_por": "caja"}
        assert calcular_monto_linea(por_unidad) == Decimal("12.50")
        assert calcular_monto_linea(por_caja) == Decimal("50.00")
