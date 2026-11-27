"""Prueba de humo del esqueleto ML (paso 0). Sin base de datos."""

import importlib

from app.ml.inferencia.cargador import cargar_modelo

MODULOS = (
    "app.ml",
    "app.ml.datasets",
    "app.ml.datasets.generar_datos",
    "app.ml.features",
    "app.ml.features.anomalias",
    "app.ml.features.pronostico",
    "app.ml.features.recomendaciones",
    "app.ml.modelos",
    "app.ml.modelos.anomalias",
    "app.ml.modelos.pronostico",
    "app.ml.modelos.recomendaciones",
    "app.ml.modelos.asistente",
    "app.ml.entrenamiento",
    "app.ml.entrenamiento.entrenar_anomalias",
    "app.ml.entrenamiento.entrenar_pronostico",
    "app.ml.entrenamiento.entrenar_recomendaciones",
    "app.ml.inferencia",
    "app.ml.inferencia.cargador",
    "app.api.v1.endpoints.ml",
    "app.api.v1.endpoints.ml.anomalias",
    "app.api.v1.endpoints.ml.pronostico",
    "app.api.v1.endpoints.ml.recomendaciones",
    "app.api.v1.endpoints.ml.asistente",
)


def test_estructura_ml():
    for nombre in MODULOS:
        assert importlib.import_module(nombre) is not None
    assert cargar_modelo("no_existe") is None
