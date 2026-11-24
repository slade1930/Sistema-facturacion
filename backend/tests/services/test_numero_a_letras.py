"""Pruebas unitarias de app.services.numero_a_letras (sin base de datos)."""

from decimal import Decimal

import pytest

from app.services.numero_a_letras import monto_a_letras_factura, numero_a_letras


class TestNumeroALetras:
    def test_cero(self):
        assert numero_a_letras(Decimal("0")) == "cero con 00/100"
        assert numero_a_letras(Decimal("0.00")) == "cero con 00/100"

    def test_unidades(self):
        assert numero_a_letras(1) == "uno con 00/100"
        assert numero_a_letras(Decimal("5.00")) == "cinco con 00/100"
        assert numero_a_letras(Decimal("9")) == "nueve con 00/100"

    def test_decenas_y_veintis(self):
        assert numero_a_letras(15) == "quince con 00/100"
        assert numero_a_letras(21) == "veintiuno con 00/100"
        assert numero_a_letras(23) == "veintitrés con 00/100"
        assert numero_a_letras(30) == "treinta con 00/100"
        assert numero_a_letras(47) == "cuarenta y siete con 00/100"

    def test_centenas(self):
        assert numero_a_letras(100) == "cien con 00/100"
        assert numero_a_letras(101) == "ciento uno con 00/100"
        assert numero_a_letras(200) == "doscientos con 00/100"
        assert numero_a_letras(999) == "novecientos noventa y nueve con 00/100"

    def test_miles(self):
        assert numero_a_letras(1000) == "mil con 00/100"
        assert numero_a_letras(2000) == "dos mil con 00/100"
        assert numero_a_letras(1234) == "mil doscientos treinta y cuatro con 00/100"

    def test_millones_y_mil_millones(self):
        assert numero_a_letras(1_000_000) == "un millón con 00/100"
        assert numero_a_letras(2_500_000) == "dos millones quinientos mil con 00/100"
        # 1e9 exacto es "mil millones", no "uno mil millones"
        assert "mil millones" in numero_a_letras(1_000_000_000)
        assert "uno mil millones" not in numero_a_letras(1_000_000_000)
        assert "mil millones" in numero_a_letras(999_999_999_999)

    def test_centavos(self):
        assert numero_a_letras(Decimal("5.05")) == "cinco con 05/100"
        assert numero_a_letras(Decimal("1234.56")) == (
            "mil doscientos treinta y cuatro con 56/100"
        )

    def test_redondeo_half_up_sube_el_entero(self):
        # 99.999 -> 100.00 con ROUND_HALF_UP: sube a "cien"
        assert numero_a_letras(Decimal("99.999")) == "cien con 00/100"
        assert numero_a_letras(Decimal("0.999")) == "uno con 00/100"
        assert numero_a_letras(Decimal("9.995")) == "diez con 00/100"

    def test_maximo_del_esquema_numeric_14_2(self):
        # 999,999,999,999.99 es el tope de Numeric(14,2)
        letras = numero_a_letras(Decimal("999999999999.99"))
        assert letras.endswith("con 99/100")
        assert "novecientos noventa y nueve mil millones" in letras

    def test_negativo_lanza_error(self):
        with pytest.raises(ValueError):
            numero_a_letras(Decimal("-1.00"))

    def test_excede_numeric_14_2_lanza_error(self):
        with pytest.raises(ValueError):
            numero_a_letras(Decimal("1000000000000.00"))

    def test_no_numerico_lanza_error(self):
        with pytest.raises(ValueError):
            numero_a_letras("abc")
        with pytest.raises(ValueError):
            numero_a_letras(None)


class TestMontoALetrasFactura:
    def test_formato_con_prefijo_y_mayusculas(self):
        assert monto_a_letras_factura(Decimal("1234.56")) == (
            "SON: MIL DOSCIENTOS TREINTA Y CUATRO CON 56/100"
        )

    def test_prefijo_personalizado(self):
        assert monto_a_letras_factura(10, prefijo="DOP").startswith("DOP:")

    def test_cero(self):
        assert monto_a_letras_factura(0) == "SON: CERO CON 00/100"
