"""Pruebas de evaluacion/pronostico.py: split temporal + baselines."""
import math

import pytest

from app.ml.evaluacion import pronostico as ev

statsmodels = pytest.importorskip("statsmodels")


def _serie(n=48):
    return [
        100 + 20 * math.sin(2 * math.pi * i / 12) + i * 0.5
        for i in range(n)
    ]


def _periodos(n=48):
    anio, mes = 2022, 1
    salida = []
    for _ in range(n):
        salida.append(f"{anio:04d}-{mes:02d}")
        mes += 1
        if mes > 12:
            mes, anio = 1, anio + 1
    return salida


def test_evaluar_serie_clasico_con_baselines():
    res = ev.evaluar_serie(
        _periodos(), _serie(), meses_prueba=6, horizonte=6, con_lstm=False
    )
    assert res["periodos_test"] == _periodos()[-6:]
    assert len(res["y_test"]) == 6
    assert set(res["metricas"]) == {
        "clasico", "mismo_mes_anterior", "media_movil"
    }
    assert len(res["predicciones"]["clasico"]) == 6
    for nombre in res["metricas"].values():
        assert nombre["n"] == 6
        assert nombre["mae"] is not None
        assert nombre["rmse"] is not None
        assert nombre["smape"] is not None


def test_evaluar_serie_split_es_temporal_no_aleatorio():
    # El holdout es siempre la cola de la serie; el modelo no la ve.
    res = ev.evaluar_serie(
        _periodos(), _serie(), meses_prueba=6, horizonte=6, con_lstm=False
    )
    serie = _serie()
    assert res["y_test"] == serie[-6:]
    # La predicción del clásico se hace tras entrenar solo con la cabeza.
    # (El artefacto no se expone, pero el holdout no entra en train por diseño.)
    assert res["periodos_test"][0] > _periodos()[-7]


def test_evaluar_serie_serie_corta_falla():
    with pytest.raises(ValueError):
        ev.evaluar_serie(_periodos(10), _serie(10), meses_prueba=6)


def test_evaluar_serie_lstm_si_torch_disponible():
    torch = pytest.importorskip("torch")
    res = ev.evaluar_serie(
        _periodos(), _serie(), meses_prueba=6, horizonte=6,
        epocas_lstm=3,
    )
    assert "lstm" in res["metricas"]
    assert res["metricas"]["lstm"]["n"] == 6


def test_evaluar_serie_lstm_opcional_apagado():
    # con_lstm=False nunca intenta importar torch.
    res = ev.evaluar_serie(
        _periodos(), _serie(), meses_prueba=6, horizonte=6, con_lstm=False
    )
    assert "lstm" not in res["metricas"]
