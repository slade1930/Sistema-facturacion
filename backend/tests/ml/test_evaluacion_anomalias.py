from datetime import date
from decimal import Decimal

import pytest

from app.ml.evaluacion import anomalias as evaluacion
from app.ml.features.anomalias import RasgosFactura
from app.ml.modelos import anomalias as modelo
from app.ml.entrenamiento import entrenar_anomalias

NOMBRE_PRUEBA = "anomalias_evaluacion.pkl"


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
def modelo_entrenado(tmp_path, monkeypatch):
    monkeypatch.setattr(modelo, "CARPETA_MODELOS", tmp_path)
    muestras = [_rasgos(i, total=str(100 + i % 7)) for i in range(60)]
    muestras += [
        _rasgos(900, total="9000"),
        _rasgos(901, descuento="80"),
        _rasgos(902, anulada=True),
    ]
    datos = modelo.entrenar(muestras, n_arboles=60)
    modelo.guardar(datos, NOMBRE_PRUEBA)
    return muestras


def test_metricas_basicas():
    resultado = evaluacion.metricas({1, 2, 3}, {2, 3, 4})

    assert resultado == {
        "tp": 2, "fp": 1, "fn": 1,
        "precision": 0.6667, "recall": 0.6667, "f1": 0.6667,
    }


def test_metricas_sin_predicciones():
    assert evaluacion.metricas([], {1, 2})["f1"] == 0.0


def test_elegir_umbral_prefiere_el_mejor_f1():
    puntajes = [(1, 0.9), (2, 0.1), (3, 0.8), (4, 0.2)]

    assert evaluacion.elegir_umbral(puntajes, {1, 2}) == 0.9


def test_sin_etiquetas_queda_el_umbral_por_defecto():
    assert evaluacion.elegir_umbral([(1, 0.9)], []) == modelo.UMBRAL_REVISION


def test_dividir_etiquetas_deja_validacion_sin_ver():
    calibracion, validacion = evaluacion.dividir_etiquetas({1, 2, 3, 4, 5})

    assert calibracion.isdisjoint(validacion)
    assert calibracion | validacion == {1, 2, 3, 4, 5}
    assert len(calibracion) == 3


def test_umbral_solo_se_calibra_con_la_primera_parte(monkeypatch, modelo_entrenado):
    vistos = []
    original = evaluacion.elegir_umbral

    def espia(puntajes, etiquetas):
        vistos.append(set(etiquetas))
        return original(puntajes, etiquetas)

    monkeypatch.setattr(evaluacion, "elegir_umbral", espia)
    evaluacion.evaluar_anomalias(
        modelo_entrenado, {900, 901, 902}, nombre=NOMBRE_PRUEBA
    )

    assert vistos == [{900, 901}]


def test_sin_modelo_no_evalua(monkeypatch):
    monkeypatch.setattr(modelo, "cargar", lambda nombre: None)

    resultado = evaluacion.evaluar_anomalias(
        [_rasgos(1)], {1}, nombre=NOMBRE_PRUEBA
    )

    assert resultado["evaluado"] is False
    assert resultado["modelo"] is None
    assert resultado["reglas"] is None
    assert resultado["isolation_forest"] is None


def test_modelo_corrupto_no_evalua(tmp_path, monkeypatch):
    monkeypatch.setattr(modelo, "CARPETA_MODELOS", tmp_path)
    (tmp_path / NOMBRE_PRUEBA).write_bytes(b"basura")

    resultado = evaluacion.evaluar_anomalias(
        [_rasgos(1)], {1}, nombre=NOMBRE_PRUEBA
    )

    assert resultado["evaluado"] is False


def test_evaluar_compara_reglas_contra_el_modelo(modelo_entrenado):
    etiquetas = {900, 901, 902}

    resultado = evaluacion.evaluar_anomalias(
        modelo_entrenado, etiquetas, nombre=NOMBRE_PRUEBA
    )

    assert resultado["evaluado"] is True
    assert resultado["modelo"] == modelo.NOMBRE_PUBLICO
    assert resultado["total"] == 63
    assert resultado["etiquetadas"] == 1
    assert resultado["calibracion"] == 2
    for clave in ("reglas", "isolation_forest"):
        assert 0 <= resultado[clave]["precision"] <= 1
        assert 0 <= resultado[clave]["recall"] <= 1
        assert 0 <= resultado[clave]["f1"] <= 1
    assert "detalle" not in resultado


def test_umbral_explicito_no_se_recalcula(modelo_entrenado):
    resultado = evaluacion.evaluar_anomalias(
        modelo_entrenado, {900}, nombre=NOMBRE_PRUEBA, umbral=0.5
    )

    assert resultado["umbral"] == 0.5


def test_detalle_incluye_cada_factura(modelo_entrenado):
    resultado = evaluacion.evaluar_anomalias(
        modelo_entrenado,
        {900, 901, 902},
        nombre=NOMBRE_PRUEBA,
        incluir_detalle=True,
    )

    assert len(resultado["detalle"]) == 63
    assert resultado["detalle"][0]["factura_id"] == 0
    assert all("puntaje" in fila for fila in resultado["detalle"])
    calibradas = [fila for fila in resultado["detalle"] if fila["factura_id"] in (900, 901)]
    assert all(
        not fila["modelo_revision"] and not fila["reglas_revision"]
        for fila in calibradas
    )


def test_rasgos_desde_fila_de_csv():
    fila = {
        "id": "12",
        "numero_serie": "F-12",
        "cliente_ruc": "RUC-1",
        "cliente_nombre": "Acme",
        "fecha": "2026-01-15",
        "total": "250.50",
        "itbms": "0.00",
        "estado": "anulada",
        "lineas": [
            {"descuento_pct": "10.00"},
            {"descuento_pct": "35.50"},
        ],
    }

    rasgos = entrenar_anomalias.rasgos_desde_fila(fila)

    assert rasgos.factura_id == 12
    assert rasgos.cliente == "RUC-1"
    assert rasgos.total == Decimal("250.50")
    assert rasgos.descuento_max_pct == Decimal("35.50")
    assert rasgos.anulada is True
    assert rasgos.numero_serie == "F-12"
    assert rasgos.cliente_ruc == "RUC-1"
    assert rasgos.itbms == Decimal("0.00")


def test_rasgos_desde_filas_marca_serie_repetida():
    filas = [
        {"id": "1", "numero_serie": "F-1", "cliente_ruc": "R", "cliente_nombre": "A",
         "fecha": "2026-01-01", "total": "10", "itbms": "1", "estado": "emitida", "lineas": []},
        {"id": "2", "numero_serie": "F-1", "cliente_ruc": "R", "cliente_nombre": "A",
         "fecha": "2026-01-02", "total": "10", "itbms": "1", "estado": "emitida", "lineas": []},
    ]

    rasgos = entrenar_anomalias.rasgos_desde_filas(filas)

    assert [f.serie_repetida for f in rasgos] == [False, True]
