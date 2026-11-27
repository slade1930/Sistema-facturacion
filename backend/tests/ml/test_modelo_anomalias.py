from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.ml.features.anomalias import RasgosFactura
from app.ml.modelos import anomalias as modelo

NOMBRE_PRUEBA = "anomalias_prueba.pkl"


def _rasgos(i, total="100", descuento="0", anulada=False, mes=1):
    return RasgosFactura(
        factura_id=i,
        cliente=f"C{i}",
        fecha=date(2026, mes, 15),
        total=Decimal(total),
        descuento_max_pct=Decimal(descuento),
        anulada=anulada,
    )


@pytest.fixture
def carpeta_modelos(tmp_path, monkeypatch):
    monkeypatch.setattr(modelo, "CARPETA_MODELOS", tmp_path)
    return tmp_path


def test_vectorizar_usa_decimal_y_orden_fijo():
    vector = modelo.vectorizar(_rasgos(1, total="250.50", descuento="12.5", anulada=True, mes=11))
    assert vector == [250.5, 12.5, 1.0, 11.0, 0.0, 0.0, 0.0]


def test_vectorizar_ve_senales_raras():
    fila = modelo.RasgosAnomalia(
        factura_id=2, cliente="", fecha=date(2026, 3, 1),
        total=Decimal("900"), descuento_max_pct=Decimal("0"), anulada=False,
        numero_serie="F-2", cliente_ruc=None, itbms=Decimal("0"), serie_repetida=True,
    )
    assert modelo.vectorizar(fila) == [900.0, 0.0, 0.0, 3.0, 1.0, 1.0, 900.0]


def test_desde_factura_copia_las_senales():
    factura = SimpleNamespace(
        id=3, cliente_nombre="Acme", cliente_ruc=None, fecha=date(2026, 4, 2),
        total=Decimal("300"), estado="emitida", numero_serie="F-3",
        itbms=Decimal("0"), lineas=[SimpleNamespace(descuento_pct=Decimal("5"))],
    )
    rasgos = modelo.desde_factura(factura, serie_repetida=True)

    assert rasgos.numero_serie == "F-3"
    assert rasgos.cliente_ruc is None
    assert rasgos.itbms == Decimal("0")
    assert rasgos.serie_repetida is True
    assert rasgos.descuento_max_pct == Decimal("5")


def test_marcar_series_repetidas_solo_la_segunda():
    filas = [
        modelo.RasgosAnomalia(1, "A", date(2026, 1, 1), Decimal("1"), Decimal("0"), False, numero_serie="F-1"),
        modelo.RasgosAnomalia(2, "B", date(2026, 1, 2), Decimal("1"), Decimal("0"), False, numero_serie="F-1"),
        modelo.RasgosAnomalia(3, "C", date(2026, 1, 3), Decimal("1"), Decimal("0"), False, numero_serie="F-2"),
    ]
    marcadas = modelo.marcar_series_repetidas(filas)

    assert [f.serie_repetida for f in marcadas] == [False, True, False]
    assert all(f.serie_repetida is False for f in filas)  # no muta las originales


def test_entrenar_sin_muestras_devuelve_none():
    assert modelo.entrenar([]) is None


def test_entrenar_es_determinista_con_la_misma_semilla():
    muestras = [
        _rasgos(i, total=str(100 + i), descuento=str(i % 20), mes=1 + i % 12)
        for i in range(40)
    ]
    uno = modelo.entrenar(muestras, n_arboles=20)
    dos = modelo.entrenar(muestras, n_arboles=20)
    otro = modelo.entrenar(muestras, n_arboles=20, semilla=7)

    assert uno["arboles"] == dos["arboles"]
    assert uno["arboles"] != otro["arboles"]


def test_guardar_y_cargar_modelo(carpeta_modelos):
    datos = modelo.entrenar([_rasgos(i) for i in range(20)], n_arboles=10)
    ruta = modelo.guardar(datos, NOMBRE_PRUEBA)

    assert ruta == carpeta_modelos / NOMBRE_PRUEBA
    assert modelo.disponible(NOMBRE_PRUEBA) is True
    assert modelo.cargar(NOMBRE_PRUEBA)["n"] == 20


def test_modelo_corrupto_no_rompe(carpeta_modelos):
    (carpeta_modelos / NOMBRE_PRUEBA).write_bytes(b"esto no es un modelo")

    assert modelo.cargar(NOMBRE_PRUEBA) is None
    assert modelo.disponible(NOMBRE_PRUEBA) is False


def test_sin_modelo_no_predice(carpeta_modelos):
    assert modelo.predecir(_rasgos(1), NOMBRE_PRUEBA) is None


def test_caso_raro_tiene_mayor_puntaje(carpeta_modelos):
    normales = [_rasgos(i, total=str(100 + i % 5)) for i in range(60)]
    datos = modelo.entrenar(normales, n_arboles=60)
    modelo.guardar(datos, NOMBRE_PRUEBA)

    normal = modelo.puntaje_con(datos, _rasgos(200, total="102"))
    raro = modelo.puntaje_con(datos, _rasgos(201, total="9000", descuento="80"))

    assert 0 <= normal < raro <= 1


def test_predecir_respeta_el_umbral(carpeta_modelos):
    normales = [_rasgos(i, total=str(100 + i % 5)) for i in range(40)]
    datos = modelo.entrenar(normales, n_arboles=40)
    modelo.guardar(datos, NOMBRE_PRUEBA)
    raro = _rasgos(99, total="9000")

    con_todo = modelo.predecir(raro, NOMBRE_PRUEBA, umbral=0.0)
    sin_nada = modelo.predecir(raro, NOMBRE_PRUEBA, umbral=1.1)

    assert con_todo.en_revision is True
    assert sin_nada.en_revision is False
