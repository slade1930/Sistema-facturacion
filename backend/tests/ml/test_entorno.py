"""Prueba rápida del entorno de ML (sin base de datos)."""

import importlib

LIBRERIAS = ("sklearn", "pandas", "numpy", "statsmodels", "joblib", "torch")


def test_librerias_ml_tienen_version():
    for nombre in LIBRERIAS:
        modulo = importlib.import_module(nombre)
        assert getattr(modulo, "__version__", None)
