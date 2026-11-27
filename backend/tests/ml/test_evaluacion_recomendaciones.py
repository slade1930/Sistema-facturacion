import pandas as pd
import pytest

from app.ml.evaluacion.recomendaciones import comparar, evaluar, preparar_casos
from app.ml.modelos import recomendaciones as modelo

PEDIDOS = {1: [1, 2, 3], 2: [1, 2], 3: [4], 4: [2, 3, 5]}


def test_preparar_casos_ignora_pedidos_de_un_producto():
    casos = preparar_casos(PEDIDOS)
    assert len(casos) == 3
    for visibles, oculto in casos:
        assert oculto not in visibles


def test_preparar_casos_es_repetible():
    assert preparar_casos(PEDIDOS) == preparar_casos(PEDIDOS)


def test_recomendador_perfecto_tiene_hit_rate_uno():
    casos = preparar_casos(PEDIDOS)
    por_oculto = {tuple(v): o for v, o in casos}
    perfecto = lambda carrito, k: [por_oculto[tuple(carrito)]]
    assert evaluar(perfecto, casos)["hit_rate"] == 1.0


def test_recomendador_que_no_acierta_tiene_hit_rate_cero():
    casos = preparar_casos(PEDIDOS)
    assert evaluar(lambda carrito, k: [999], casos)["hit_rate"] == 0.0


def test_sin_modelo_dice_sin_evaluar():
    casos = preparar_casos(PEDIDOS)
    res = comparar(None, lambda c, k: [1, 2, 3], casos)
    assert res["modelo"] == "sin evaluar"
    assert res["linea_base"]["casos"] == 3


def test_comparar_autoencoder_contra_linea_base():
    pytest.importorskip("torch")
    matriz = pd.DataFrame(
        [
            [1.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
        ],
        index=["A", "B", "C", "D", "E"],
        columns=[1, 2, 3, 4],
    )
    artefacto = modelo.entrenar_autoencoder(matriz, ocultas=4, epocas=5)

    def recomendador(carrito, k):
        items = modelo.recomendar(artefacto, carrito, n=k)
        return [item["producto_id"] for item in items]

    casos = preparar_casos(PEDIDOS)
    resultado = comparar(recomendador, lambda c, k: [1, 2, 3], casos, k=3)

    assert isinstance(resultado["modelo"], dict)
    assert resultado["modelo"]["casos"] == resultado["linea_base"]["casos"]
    assert 0.0 <= resultado["modelo"]["hit_rate"] <= 1.0