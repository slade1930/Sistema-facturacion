from datetime import date
from decimal import Decimal

from app.ml.features.anomalias import RasgosFactura
from app.ml.reglas.anomalias import (
    percentil,
    regla_anulaciones_repetidas,
    regla_descuento_alto,
    regla_duplicado,
    regla_monto_alto,
)

def _factura(i, total, cliente="C1", descuento="0", anulada=False):
    return RasgosFactura(
        factura_id=i,
        cliente=cliente,
        fecha=date(2026, 1, 1),
        total=Decimal(str(total)),
        descuento_max_pct=Decimal(descuento),
        anulada=anulada,
    )


def test_percentil_de_1_a_100():
    assert percentil([Decimal(x) for x in range(1, 101)], 50) == Decimal("50.5")


def test_monto_muy_alto_salta():
    historial = [_factura(i, 100 + i) for i in range(30)]
    hallazgo = regla_monto_alto(_factura(99, 5000), historial)
    assert hallazgo.regla == "monto_alto"


def test_monto_normal_no_salta():
    historial = [_factura(i, 100 + i) for i in range(30)]
    assert regla_monto_alto(_factura(98, 110), historial) is None


def test_poco_historial_no_evalua():
    historial = [_factura(i, 100 + i) for i in range(5)]
    assert regla_monto_alto(_factura(97, 5000), historial) is None

def test_descuento_alto_salta():
    assert regla_descuento_alto(_factura(1, 100, descuento="50")).regla == "descuento_alto"


def test_descuento_en_el_limite_no_salta():
    assert regla_descuento_alto(_factura(1, 100, descuento="30")) is None


def test_descuento_normal_no_salta():
    assert regla_descuento_alto(_factura(1, 100, descuento="10")) is None


def test_duplicado_salta():
    base = _factura(1, 100)
    assert regla_duplicado(base, [_factura(2, 100)]).regla == "duplicado"


def test_distinto_total_no_es_duplicado():
    assert regla_duplicado(_factura(1, 100), [_factura(2, 101)]) is None


def test_distinto_cliente_no_es_duplicado():
    assert regla_duplicado(_factura(1, 100), [_factura(2, 100, cliente="C2")]) is None


def test_no_se_compara_consigo_misma():
    base = _factura(1, 100)
    assert regla_duplicado(base, [base]) is None

def test_anulaciones_repetidas_salta():
    base = _factura(1, 100, anulada=True)
    historial = [_factura(2, 100, anulada=True), _factura(3, 100, anulada=True)]
    assert regla_anulaciones_repetidas(base, historial).regla == "anulaciones_repetidas"


def test_dos_anulaciones_no_salta():
    base = _factura(1, 100, anulada=True)
    assert regla_anulaciones_repetidas(base, [_factura(2, 100, anulada=True)]) is None


def test_factura_no_anulada_no_salta():
    historial = [_factura(i, 100, anulada=True) for i in (2, 3, 4)]
    assert regla_anulaciones_repetidas(_factura(1, 100), historial) is None


def test_anulaciones_de_otro_cliente_no_cuentan():
    historial = [_factura(i, 100, cliente="C2", anulada=True) for i in (2, 3)]
    assert regla_anulaciones_repetidas(_factura(1, 100, anulada=True), historial) is None


def test_anulaciones_no_se_cuenta_a_si_misma():
    base = _factura(1, 100, anulada=True)
    assert regla_anulaciones_repetidas(base, [base, _factura(2, 100, anulada=True)]) is None