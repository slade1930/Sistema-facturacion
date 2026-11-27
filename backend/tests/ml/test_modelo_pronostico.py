"""Pruebas del modelo clásico de pronóstico (SARIMAX/Holt-Winters)."""
import math

import pytest

from app.ml.datasets import generar_datos as gd
from app.ml.entrenamiento import entrenar_pronostico as ent
from app.ml.modelos import pronostico as modelos

pytest.importorskip("statsmodels")
pytest.importorskip("joblib")


def _serie_estacional(n=36):
    return [
        100 + 20 * math.sin(2 * math.pi * i / 12) + i * 0.5
        for i in range(n)
    ]


def test_entrenar_y_predecir_devuelve_horizonte():
    modelo = modelos.entrenar_modelo(_serie_estacional(), horizonte=6)
    pred = modelos.predecir(modelo, horizonte=6)
    assert pred is not None and len(pred) == 6
    assert all(math.isfinite(v) for v in pred)


def test_fallback_holt_winters_tambien_predice():
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    resultado = ExponentialSmoothing(
        _serie_estacional(), trend="add", seasonal="add",
        seasonal_periods=12,
    ).fit()
    modelo = {"resultado": resultado}
    pred = modelos.predecir(modelo, horizonte=3)
    assert pred is not None and len(pred) == 3


def test_sin_modelo_devuelve_none():
    assert modelos.predecir(None, 6) is None
    assert modelos.cargar_modelo("no_existe.joblib") is None


def test_metricas_valores_conocidos():
    m = modelos.metricas([10, 20], [12, 18])
    assert m["n"] == 2
    assert m["mae"] == pytest.approx(2.0)
    assert m["rmse"] == pytest.approx(2.0)
    assert m["smape"] > 0


def test_baselines_coherentes():
    h = list(range(24))
    na = modelos.baseline_mismo_mes_anterior(h, 3, estacional=12)
    assert na == [h[12], h[13], h[14]]
    mm = modelos.baseline_media_movil(h, 4, ventana=12)
    assert mm == [pytest.approx(sum(h[-12:]) / 12)] * 4


def test_entrenamiento_split_temporal(tmp_path):
    dataset = gd.construir_dataset(n_facturas=400, n_pedidos=0)
    gd.escribir_csvs(dataset, tmp_path)

    res = ent.entrenar(
        directorio=tmp_path, meses_prueba=6,
        directorio_modelos=tmp_path / "modelos",
    )
    # Split temporal: test = últimos 6 periodos, train = todo lo anterior.
    assert len(res["periodos_test"]) == 6
    assert res["periodos_train"][-1] < res["periodos_test"][0]
    assert set(res["metricas"]) == {
        "modelo", "mismo_mes_anterior", "media_movil"
    }
    ruta = tmp_path / "modelos" / "pronostico_clasico.joblib"
    assert res["ruta_modelo"] and ruta.is_file()
