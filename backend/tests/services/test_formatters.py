"""Pruebas unitarias de app.utils.formatters (sin base de datos)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.utils.formatters import (
    formato_fecha,
    formato_fecha_hora,
    formato_moneda,
    formato_porcentaje,
    formato_ruc,
)


class TestFormatoMoneda:
    def test_miles_y_centavos(self):
        assert formato_moneda(Decimal("1234.5")) == "1,234.50"
        assert formato_moneda(Decimal("0")) == "0.00"
        assert formato_moneda(Decimal("999999.99")) == "999,999.99"

    def test_redondeo_half_up(self):
        # 1.005 -> 1.01 con HALF_UP (format() solo daría half-even)
        assert formato_moneda(Decimal("1.005")) == "1.01"
        assert formato_moneda(Decimal("2.675")) == "2.68"

    def test_negativo(self):
        assert formato_moneda(Decimal("-1234.5")) == "-1,234.50"

    def test_con_simbolo(self):
        assert formato_moneda(Decimal("10"), "USD") == "10.00 USD"

    def test_acepta_str_y_float_sueltos(self):
        assert formato_moneda("10.5") == "10.50"


class TestFormatoFecha:
    def test_date_a_ddmmyyyy(self):
        assert formato_fecha(date(2026, 11, 24)) == "24/11/2026"

    def test_datetime_usa_solo_fecha(self):
        assert formato_fecha(datetime(2026, 1, 5, 18, 30)) == "05/01/2026"

    def test_str_pasa_intacto(self):
        assert formato_fecha("2026-11-24") == "2026-11-24"

    def test_none_devuelve_vacio(self):
        assert formato_fecha(None) == ""


class TestFormatoFechaHora:
    def test_datetime_completo(self):
        assert formato_fecha_hora(datetime(2026, 11, 24, 9, 5)) == "24/11/2026 09:05"

    def test_solo_date_cae_a_fecha(self):
        assert formato_fecha_hora(date(2026, 11, 24)) == "24/11/2026"


class TestFormatoPorcentajeYRuc:
    def test_porcentaje(self):
        assert formato_porcentaje(Decimal("7")) == "7.00%"
        assert formato_porcentaje(Decimal("7.5"), decimales=1) == "7.5%"

    def test_ruc_limpia_espacios(self):
        assert formato_ruc("  8-123-456  ") == "8-123-456"
        assert formato_ruc(None) == ""
