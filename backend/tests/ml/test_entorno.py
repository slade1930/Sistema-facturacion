"""Prueba rápida del entorno de ML (sin base de datos)."""

import importlib

import pytest

LIBRERIAS = ("sklearn", "pandas", "numpy", "statsmodels", "joblib", "torch")


def test_librerias_ml_tienen_version():
    for nombre in LIBRERIAS:
        modulo = pytest.importorskip(
            nombre, reason="Dependencia ML no instalada (requirements-ml.txt)"
        )
        assert getattr(modulo, "__version__", None)
