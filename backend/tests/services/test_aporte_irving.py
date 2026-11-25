"""Pruebas del aporte de Irving (Equipo 2: lógica de facturación).

Cubre sin base de datos real:
- Series de Orden de Compra (OC-AAAA-####) y extraer_anio.
- Casos borde de app.utils.validators (Decimal, ROUND_HALF_UP vía totales,
  descuentos 0 y 100, valores inválidos).
- Formateadores de app.utils.formatters.
- Conversión a letras de app.services.numero_a_letras.

No se usa Postgres: los contadores de serie se prueban con una sesión
falsa, igual que en test_serie.py.
"""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import numero_a_letras, serie
from app.utils import formatters, validators


# ---------------------------------------------------------------------------
# Sesión falsa (misma idea que test_serie.py): execute() devuelve la fila del
# contador; flush() solo se registra. No hay commit() a propósito.
# ---------------------------------------------------------------------------

class _ResultadoFalso:
    def __init__(self, fila):
        self._fila = fila

    def scalar_one(self):
        return self._fila


class _SesionFalsa:
    def __init__(self, fila):
        self._fila = fila
        self.flushes = 0

    def execute(self, _sentencia):
        return _ResultadoFalso(self._fila)

    def flush(self):
        self.flushes += 1


# ---------------------------------------------------------------------------
# Series de Orden de Compra: OC-AAAA-####
# ---------------------------------------------------------------------------

class TestSerieOrdenCompra:
    def test_formato_oc_cuatro_digitos(self):
        assert serie._formato(serie.PREFIJO_ORDEN_COMPRA, 2026, 1) == "OC-2026-0001"
        assert serie._formato(serie.PREFIJO_ORDEN_COMPRA, 2026, 42) == "OC-2026-0042"
        assert serie._formato(serie.PREFIJO_ORDEN_COMPRA, 2025, 12345) == "OC-2025-12345"

    def test_prefijo_oc_publico(self):
        assert serie.PREFIJO_ORDEN_COMPRA == "OC"

    def test_siguiente_numero_oc_formato_y_flush(self):
        fila = SimpleNamespace(ultimo_numero=9)
        db = _SesionFalsa(fila)

        folio = serie.siguiente_numero_oc(db, 2026)

        assert folio == "OC-2026-0010"
        assert fila.ultimo_numero == 10
        assert db.flushes == 1

    def test_siguiente_numero_oc_consecutivos(self):
        fila = SimpleNamespace(ultimo_numero=0)
        db = _SesionFalsa(fila)

        assert serie.siguiente_numero_oc(db, 2026) == "OC-2026-0001"
        assert serie.siguiente_numero_oc(db, 2026) == "OC-2026-0002"

    def test_serie_oc_valida(self):
        assert validators.es_serie_oc_valida("OC-2026-0001")
        assert validators.es_serie_oc_valida("OC-1999-9999")
        # Un folio FAC no es una serie OC válida y viceversa.
        assert not validators.es_serie_oc_valida("FAC-2026-0001")
        assert not validators.es_serie_factura_valida("OC-2026-0001")
        # Formatos inválidos.
        for mala in ("OC-2026-1", "OC-26-0001", "OC2026-0001", "OC-2026-000", ""):
            assert not validators.es_serie_oc_valida(mala), mala

    def test_extraer_anio_folios_oc(self):
        assert validators.extraer_anio("OC-2026-0001") == 2026
        assert validators.extraer_anio("OC-1999-1234") == 1999
        assert validators.extraer_anio("FAC-2024-0007") == 2024

    def test_extraer_anio_invalido_lanza_valueerror(self):
        for mala in ("OC-2026-1", "sin-formato", "", None):
            with pytest.raises(ValueError):
                validators.extraer_anio(mala)


# ---------------------------------------------------------------------------
# Casos borde de app.utils.validators
# ---------------------------------------------------------------------------

class TestAdecimal:
    def test_acepta_decimal_int_str_y_float(self):
        assert validators.a_decimal(Decimal("1.5")) == Decimal("1.5")
        assert validators.a_decimal(3) == Decimal("3")
        assert validators.a_decimal("12.34") == Decimal("12.34")
        assert validators.a_decimal(0.1) == Decimal("0.1")

    @pytest.mark.parametrize("malo", [None, True, False, "abc", "", "NaN", "Infinity", "-inf"])
    def test_rechaza_valores_invalidos(self, malo):
        with pytest.raises(ValueError):
            validators.a_decimal(malo)


class TestDescuentoYLimites:
    def test_descuento_cero_y_cien_son_validos(self):
        assert validators.validar_descuento_pct(0) == Decimal("0")
        assert validators.validar_descuento_pct(Decimal("100")) == Decimal("100")
        assert validators.validar_descuento_pct("50.5") == Decimal("50.5")

    @pytest.mark.parametrize("malo", [-0.01, -1, "101", Decimal("100.01"), "abc", None])
    def test_descuento_fuera_de_rango(self, malo):
        with pytest.raises(ValueError):
            validators.validar_descuento_pct(malo)

    def test_cantidad_minima(self):
        assert validators.validar_cantidad(Decimal("0.01")) == Decimal("0.01")
        for mala in (Decimal("0"), Decimal("0.009"), 0, "abc", None):
            with pytest.raises(ValueError):
                validators.validar_cantidad(mala)

    def test_precio_no_negativo(self):
        assert validators.validar_precio(0) == Decimal("0")
        assert validators.validar_precio(Decimal("9.99")) == Decimal("9.99")
        for malo in (-1, Decimal("-0.01"), "-5", None):
            with pytest.raises(ValueError):
                validators.validar_precio(malo)

    def test_unidades_por_caja_entero_positivo(self):
        assert validators.validar_unidades_por_caja(1) == 1
        assert validators.validar_unidades_por_caja(12) == 12
        for malo in (0, -3, True, "5", 1.5, None):
            with pytest.raises(ValueError):
                validators.validar_unidades_por_caja(malo)


class TestTotalesHalfUp:
    """ROUND_HALF_UP en totales.py: los montos nunca usan float."""

    def test_monto_linea_redondea_half_up(self):
        from app.services.totales import calcular_monto_linea

        # 3 x 0.335 = 1.005 -> bruto 1.01 (HALF_UP, no half-even)
        linea = {"cantidad": "3", "precio_unitario": "0.335", "descuento_pct": 0}
        assert calcular_monto_linea(linea) == Decimal("1.01")

    def test_descuento_cero_y_cien(self):
        from app.services.totales import calcular_monto_linea

        base = {"cantidad": "2", "precio_unitario": "10.00"}
        assert calcular_monto_linea({**base, "descuento_pct": 0}) == Decimal("20.00")
        assert calcular_monto_linea({**base, "descuento_pct": 100}) == Decimal("0.00")

    def test_itbms_solo_sobre_lineas_gravadas(self):
        from app.services.totales import calcular_totales

        lineas = [
            {"cantidad": "1", "precio_unitario": "100.00", "descuento_pct": 0, "gravada": True},
            {"cantidad": "1", "precio_unitario": "50.00", "descuento_pct": 0, "gravada": False},
        ]
        t = calcular_totales(lineas)
        assert t["base_gravada"] == Decimal("100.00")
        assert t["base_exenta"] == Decimal("50.00")
        assert t["itbms"] == Decimal("7.00")  # 7% solo de 100.00
        assert t["total"] == Decimal("157.00")


# ---------------------------------------------------------------------------
# Formateadores
# ---------------------------------------------------------------------------

class TestFormateadores:
    def test_formato_moneda(self):
        assert formatters.formato_moneda(Decimal("1234.5")) == "1,234.50"
        assert formatters.formato_moneda(Decimal("-10")) == "-10.00"
        assert formatters.formato_moneda(Decimal("1.005")) == "1.01"  # HALF_UP
        assert formatters.formato_moneda(Decimal("10"), "USD") == "10.00 USD"

    def test_formato_porcentaje(self):
        assert formatters.formato_porcentaje(Decimal("7")) == "7.00%"
        assert formatters.formato_porcentaje(Decimal("7.5"), decimales=1) == "7.5%"
        assert formatters.formato_porcentaje(Decimal("2.675"), decimales=2) == "2.68%"

    def test_formato_fecha(self):
        assert formatters.formato_fecha(date(2026, 11, 24)) == "24/11/2026"
        assert formatters.formato_fecha(datetime(2026, 1, 5, 18, 30)) == "05/01/2026"
        assert formatters.formato_fecha("2026-11-24") == "2026-11-24"
        assert formatters.formato_fecha(None) == ""

    def test_formato_ruc(self):
        assert formatters.formato_ruc("  8-123-456  ") == "8-123-456"
        assert formatters.formato_ruc(None) == ""
        assert formatters.formato_ruc(12345678) == "12345678"


# ---------------------------------------------------------------------------
# Conversión a letras
# ---------------------------------------------------------------------------

class TestNumeroALetras:
    def test_casos_basicos(self):
        assert numero_a_letras.numero_a_letras(0) == "cero con 00/100"
        assert numero_a_letras.numero_a_letras(Decimal("1")) == "uno con 00/100"
        assert numero_a_letras.numero_a_letras(Decimal("1234.56")) == (
            "mil doscientos treinta y cuatro con 56/100"
        )

    def test_redondeo_half_up_puede_subir_el_entero(self):
        # 99.999 -> 100.00 -> "cien con 00/100"
        assert numero_a_letras.numero_a_letras(Decimal("99.999")) == "cien con 00/100"
        assert numero_a_letras.numero_a_letras(Decimal("0.005")) == "cero con 01/100"

    def test_montos_grandes(self):
        assert numero_a_letras.numero_a_letras(Decimal("1000000")) == (
            "un millón con 00/100"
        )
        assert numero_a_letras.numero_a_letras(Decimal("1000000000")) == (
            "mil millones con 00/100"
        )

    def test_negativo_y_exceso_lanzan_valueerror(self):
        with pytest.raises(ValueError):
            numero_a_letras.numero_a_letras(-1)
        with pytest.raises(ValueError):
            numero_a_letras.numero_a_letras(Decimal("9999999999999.99"))

    def test_monto_a_letras_factura(self):
        assert numero_a_letras.monto_a_letras_factura(Decimal("1234.56")) == (
            "SON: MIL DOSCIENTOS TREINTA Y CUATRO CON 56/100"
        )
        assert numero_a_letras.monto_a_letras_factura(Decimal("10"), "USD") == (
            "USD: DIEZ CON 00/100"
        )
