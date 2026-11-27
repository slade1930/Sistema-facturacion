"""Pruebas del autoencoder de recomendaciones (Módulo 3).

Datos sintéticos en memoria, sin CSV versionados y sin base de datos.
Las pruebas que necesitan torch se omiten solas si no está instalado.
"""
import pandas as pd
import pytest

from app.ml.modelos import recomendaciones as modelo


def _matriz():
    return pd.DataFrame(
        [
            [1.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
        ],
        index=["A", "B", "C", "D", "E"],
        columns=[10, 20, 30, 40],
    )


def test_disponible_refleja_torch():
    assert isinstance(modelo.disponible(), bool)


def test_entrenar_sin_datos_devuelve_none():
    assert modelo.entrenar_autoencoder(None) is None
    assert modelo.entrenar_autoencoder(pd.DataFrame()) is None
    # Una sola columna no alcanza para recomendar.
    assert modelo.entrenar_autoencoder(pd.DataFrame({1: [0, 1]})) is None


def test_artefacto_invalido_no_recomienda():
    assert modelo.recomendar(None, [1]) is None
    assert modelo.recomendar({"tipo": "otro"}, [1]) is None
    assert modelo.recomendar({"tipo": "autoencoder"}, [1]) is None


def test_guardar_y_cargar_artefacto(tmp_path):
    pytest.importorskip("torch")
    artefacto = modelo.entrenar_autoencoder(
        _matriz(), ocultas=4, epocas=5, semilla=7
    )
    assert artefacto is not None

    ruta = modelo.guardar_modelo(artefacto, tmp_path)
    assert ruta.is_file()
    cargado = modelo.cargar_modelo(ruta)
    assert cargado["tipo"] == "autoencoder"
    assert cargado["productos"] == [10, 20, 30, 40]

    (tmp_path / "roto.pt").write_bytes(b"no es un modelo")
    assert modelo.cargar_modelo(tmp_path / "roto.pt") is None


def test_recomienda_sin_devolver_lo_que_ya_esta_ni_excluidos():
    pytest.importorskip("torch")
    artefacto = modelo.entrenar_autoencoder(
        _matriz(), ocultas=4, epocas=5, semilla=7
    )
    assert artefacto is not None

    resultados = modelo.recomendar(
        artefacto, [10], n=2, excluir=[40]
    )
    assert len(resultados) == 2
    assert {item["producto_id"] for item in resultados} <= {20, 30}
    assert all(item["fuente"] == "autoencoder" for item in resultados)
    assert all(0.0 <= item["puntaje"] <= 1.0 for item in resultados)


def test_misma_semilla_da_las_mismas_recomendaciones():
    torch = pytest.importorskip("torch")
    primero = modelo.entrenar_autoencoder(
        _matriz(), ocultas=4, epocas=5, semilla=123
    )
    segundo = modelo.entrenar_autoencoder(
        _matriz(), ocultas=4, epocas=5, semilla=123
    )
    for nombre, tensor in primero["estado"].items():
        assert torch.equal(tensor, segundo["estado"][nombre])
    assert modelo.recomendar(primero, [10], n=3) == modelo.recomendar(
        segundo, [10], n=3
    )
