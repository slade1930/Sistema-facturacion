"""Pruebas del modelo LSTM de pronóstico (PyTorch CPU).

Sin torch instalado todo el módulo se salta (importorskip).
"""
import math

import pytest

from app.ml.datasets import generar_datos as gd
from app.ml.entrenamiento import entrenar_pronostico_lstm as ent
from app.ml.modelos import pronostico_lstm as lstm

pytest.importorskip("torch")


def _serie(n=48):
    return [
        100 + 20 * math.sin(2 * math.pi * i / 12) + i * 0.4
        for i in range(n)
    ]


def test_preparar_ventanas_formas():
    X, Y = lstm.preparar_ventanas(_serie(40), ventana=12, horizonte=6)
    assert len(X) == len(Y) == 40 - 12 - 6 + 1
    assert len(X[0]) == 12 and len(Y[0]) == 6
    # La ventana y el objetivo son contiguos y sin solape.
    serie = _serie(40)
    assert X[0] == serie[0:12]
    assert Y[0] == serie[12:18]


def test_serie_corta_falla():
    with pytest.raises(ValueError):
        lstm.preparar_ventanas([1.0] * 10)


def test_entrenar_y_predecir(tmp_path):
    modelo = lstm.entrenar_lstm(
        _serie(), horizonte=6, epocas=5, semilla=1
    )
    pred = lstm.predecir(modelo, horizonte=6)
    assert pred is not None and len(pred) == 6
    assert all(math.isfinite(v) for v in pred)


def test_sin_modelo_devuelve_none():
    assert lstm.predecir(None, 6) is None
    assert lstm.cargar_modelo("no_existe.pt") is None


def test_guardar_y_cargar(tmp_path):
    modelo = lstm.entrenar_lstm(_serie(), horizonte=6, epocas=3, semilla=1)
    ruta = lstm.guardar_modelo(modelo, tmp_path)
    assert ruta.is_file()
    cargado = lstm.cargar_modelo(ruta)
    assert cargado is not None
    pred = lstm.predecir(cargado, horizonte=6)
    assert pred is not None and len(pred) == 6


def test_entrenamiento_split_temporal(tmp_path):
    dataset = gd.construir_dataset(n_facturas=400, n_pedidos=0)
    gd.escribir_csvs(dataset, tmp_path)

    res = ent.entrenar(
        directorio=tmp_path, meses_prueba=6, epocas=5,
        directorio_modelos=tmp_path / "modelos",
    )
    # Split temporal: test = últimos 6 periodos, train = todo lo anterior.
    assert len(res["periodos_test"]) == 6
    assert res["periodos_train"][-1] < res["periodos_test"][0]
    assert set(res["metricas"]) == {
        "lstm", "mismo_mes_anterior", "media_movil"
    }
    for nombre in ("lstm", "mismo_mes_anterior", "media_movil"):
        assert res["metricas"][nombre] is not None
        assert res["metricas"][nombre]["n"] == 6
    ruta = tmp_path / "modelos" / "pronostico_lstm.pt"
    assert res["ruta_modelo"] and ruta.is_file()


def test_predecir_horizonte_menor_al_entrenado():
    """La red se carga con su cabeza de 6 y se recorta a lo pedido."""
    modelo = lstm.entrenar_lstm(_serie(), horizonte=6, epocas=3, semilla=1)
    pred = lstm.predecir(modelo, horizonte=3)
    assert pred is not None and len(pred) == 3
    assert all(math.isfinite(v) for v in pred)


def test_predecir_horizonte_mayor_al_entrenado_devuelve_none():
    """Pedir más meses de los que la red sabe dar no inventa valores."""
    modelo = lstm.entrenar_lstm(_serie(), horizonte=6, epocas=3, semilla=1)
    assert lstm.predecir(modelo, horizonte=12) is None
