import pandas as pd
import pytest

from app.ml.entrenamiento.entrenar_recomendaciones import entrenar_desde_dataset
from app.ml.modelos.recomendaciones import (
    ARCHIVO_MODELO,
    cargar_modelo,
    disponible,
    entrenar_autoencoder,
    guardar_modelo,
    predecir,
    recomendar,
)

pytestmark = pytest.mark.skipif(
    not disponible(), reason="PyTorch no está instalado en este entorno"
)


def _matriz_sintetica():
    return pd.DataFrame(
        [
            [1.0, 1.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 0.0],
            [0.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
        ],
        index=["c1", "c2", "c3", "c4"],
        columns=[10, 20, 30, 40],
    )


def _dataset_sintetico():
    return {
        "facturas": [
            {
                "id": 1,
                "estado": "emitida",
                "cliente_ruc": "RUC-1",
                "fecha": "2026-11-01",
                "lineas": [
                    {"producto_id": 10, "cantidad": 2, "monto": 20},
                    {"producto_id": 20, "cantidad": 1, "monto": 10},
                ],
            },
            {
                "id": 2,
                "estado": "emitida",
                "cliente_ruc": "RUC-2",
                "fecha": "2026-11-02",
                "lineas": [
                    {"producto_id": 20, "cantidad": 1, "monto": 10},
                    {"producto_id": 30, "cantidad": 3, "monto": 30},
                ],
            },
            {
                "id": 3,
                "estado": "emitida",
                "cliente_ruc": "RUC-3",
                "fecha": "2026-11-03",
                "lineas": [
                    {"producto_id": 10, "cantidad": 1, "monto": 10},
                    {"producto_id": 30, "cantidad": 2, "monto": 20},
                    {"producto_id": 40, "cantidad": 1, "monto": 15},
                ],
            },
        ],
        "pedidos": [],
    }


def test_entrenar_con_matriz_insuficiente_devuelve_none():
    assert entrenar_autoencoder(pd.DataFrame()) is None
    solo_uno = pd.DataFrame([[1.0]], index=["c1"], columns=[10])
    assert entrenar_autoencoder(solo_uno) is None


def test_entrenar_recomendar_y_excluir():
    modelo = entrenar_autoencoder(_matriz_sintetica(), ocultas=4, epocas=20)
    assert modelo is not None
    assert modelo["tipo"] == "autoencoder"
    assert modelo["productos"] == [10, 20, 30, 40]

    recs = recomendar(modelo, productos_en_cesta=[10], n=2, excluir=[40])
    assert recs is not None
    assert len(recs) == 2
    ids = {r["producto_id"] for r in recs}
    assert 10 not in ids
    assert 40 not in ids
    assert all(r["fuente"] == "autoencoder" for r in recs)
    assert predecir(modelo, [10], n=2, excluir=[40]) == recs


def test_recomendar_sin_modelo_devuelve_none():
    assert recomendar(None, [10]) is None
    assert recomendar({"tipo": "otro"}, [10]) is None


def test_guardar_y_cargar_modelo(tmp_path):
    modelo = entrenar_autoencoder(_matriz_sintetica(), ocultas=4, epocas=10)
    ruta = guardar_modelo(modelo, directorio=tmp_path)
    assert ruta == tmp_path / ARCHIVO_MODELO
    assert ruta.is_file()

    cargado = cargar_modelo(ruta)
    assert cargado is not None
    assert cargado["productos"] == modelo["productos"]
    assert cargar_modelo(tmp_path / "inexistente.pt") is None


def test_entrenar_desde_dataset_sintetico(tmp_path):
    modelo, ruta = entrenar_desde_dataset(
        _dataset_sintetico(),
        directorio_salida=tmp_path,
        ocultas=4,
        epocas=15,
    )
    assert modelo is not None
    assert ruta is not None and ruta.is_file()
