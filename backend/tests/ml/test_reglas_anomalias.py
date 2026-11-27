from datetime import date
from decimal import Decimal

from app.ml.features.anomalias import RasgosFactura
from app.ml.reglas.anomalias import (
    evaluar_factura,
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


def test_factura_normal_puntaje_cero():
    resultado = evaluar_factura(_factura(1, 100), [])
    assert resultado.puntaje == 0
    assert resultado.hallazgos == []


def test_una_regla_suma_su_peso():
    resultado = evaluar_factura(_factura(1, 100, descuento="50"), [])
    assert resultado.puntaje == 25
    assert [h.regla for h in resultado.hallazgos] == ["descuento_alto"]


def test_dos_reglas_suman_sus_pesos():
    resultado = evaluar_factura(_factura(1, 100, descuento="50"), [_factura(2, 100)])
    assert resultado.puntaje == 55  # 25 del descuento + 30 del duplicado


def test_todas_las_reglas_se_topan_en_100():
    historial = [_factura(i, 100 + i) for i in range(30)]
    historial.append(_factura(100, 5000))  # mismo total: provoca el duplicado
    historial.append(_factura(101, 100, anulada=True))
    historial.append(_factura(102, 100, anulada=True))
    factura = _factura(99, 5000, descuento="50", anulada=True)

    resultado = evaluar_factura(factura, historial)

    assert len(resultado.hallazgos) == 4  # los pesos suman 115
    assert resultado.puntaje == 100


def test_duplicado_ignora_mayusculas_y_sufijo():
    base = _factura(1, 100, cliente="Acme S.A.")
    otra = _factura(2, 100, cliente="acme s.a.")
    assert regla_duplicado(base, [otra]).regla == "duplicado"


def test_duplicado_ruc_y_nombre_no_coinciden():
    base = _factura(1, 100, cliente="RUC-123")
    otra = _factura(2, 100, cliente="RUC 123")
    assert regla_duplicado(base, [otra]).regla == "duplicado"


def test_cliente_parecido_no_es_duplicado():
    base = _factura(1, 100, cliente="Acme Sur")
    otra = _factura(2, 100, cliente="Acme Norte")
    assert regla_duplicado(base, [otra]) is None


def test_anulaciones_de_nombre_y_ruc_cuentan_juntas():
    base = _factura(1, 100, cliente="Juan Pérez", anulada=True)
    historial = [
        _factura(2, 100, cliente="juan perez", anulada=True),
        _factura(3, 100, cliente="Juan  Perez", anulada=True),
    ]
    assert regla_anulaciones_repetidas(base, historial).regla == "anulaciones_repetidas"


def test_rasgos_desde_factura_real():
    from datetime import date as _date
    from decimal import Decimal as _Decimal

    from app.models.facturacion import EstadoFactura, Factura, LineaFactura
    from app.ml.features.anomalias import rasgos_de_factura

    factura = Factura(
        id=7,
        numero_serie="F-7",
        codigo_verificacion="ABC123",
        fecha=_date(2026, 1, 1),
        cliente_nombre="Acme S.A.",
        cliente_ruc=None,
        estado=EstadoFactura.ANULADA,
        total=_Decimal("5000.00"),
        lineas=[LineaFactura(descuento_pct=_Decimal("50.00"))],
    )
    rasgos = rasgos_de_factura(factura)
    assert rasgos.factura_id == 7
    assert rasgos.cliente == "Acme S.A."
    assert rasgos.total == _Decimal("5000.00")
    assert rasgos.descuento_max_pct == _Decimal("50.00")
    assert rasgos.anulada is True


def test_rasgos_de_factura_sin_lineas():
    from datetime import date as _date
    from decimal import Decimal as _Decimal

    from app.models.facturacion import EstadoFactura, Factura
    from app.ml.features.anomalias import rasgos_de_factura

    factura = Factura(
        id=8,
        numero_serie="F-8",
        codigo_verificacion="DEF456",
        fecha=_date(2026, 1, 2),
        cliente_nombre="Beta",
        cliente_ruc="RUC-1",
        estado=EstadoFactura.EMITIDA,
        total=_Decimal("10.00"),
        lineas=[],
    )
    rasgos = rasgos_de_factura(factura)
    assert rasgos.cliente == "RUC-1"
    assert rasgos.descuento_max_pct == _Decimal("0")
    assert rasgos.anulada is False
