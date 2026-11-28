"""Parámetros PBKDF2 y coste parecido del hash falso."""

import statistics
import time

import pytest

from app.core.config import settings
from app.services import auth

CLAVE_PRUEBA = "Clave1234"
ITERACIONES_PRUEBA = 100_000


def test_endurecimiento_pbkdf2_usa_parametros_de_configuracion():
    assert settings.AUTH_PBKDF2_ITERATIONS >= 600_000
    assert auth._iteraciones() == settings.AUTH_PBKDF2_ITERATIONS

    guardado = auth.hash_clave(CLAVE_PRUEBA)
    algoritmo, iteraciones, sal, digest = guardado.split("$")

    assert algoritmo == "pbkdf2_sha256"
    assert int(iteraciones) == settings.AUTH_PBKDF2_ITERATIONS
    assert sal and digest
    assert auth.verificar_clave(CLAVE_PRUEBA, guardado)
    assert not auth.verificar_clave(CLAVE_PRUEBA + "distinta", guardado)


def _tiempo_verificacion(clave: str, guardado: str) -> float:
    inicio = time.perf_counter()
    auth.verificar_clave(clave, guardado)
    return time.perf_counter() - inicio


def test_endurecimiento_hash_falso_tiene_coste_parecido(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(auth, "_iteraciones", lambda: ITERACIONES_PRUEBA)
    real = auth.hash_clave(CLAVE_PRUEBA)
    falso = auth._hash_falso(ITERACIONES_PRUEBA)

    assert int(falso.split("$")[1]) == ITERACIONES_PRUEBA
    assert falso != real
    assert not auth.verificar_clave(CLAVE_PRUEBA, falso)

    # Calentamiento para no medir importaciones ni creación del caché.
    _tiempo_verificacion(CLAVE_PRUEBA, real)
    _tiempo_verificacion(CLAVE_PRUEBA, falso)
    tiempos_reales = [
        _tiempo_verificacion(CLAVE_PRUEBA, real) for _ in range(3)
    ]
    tiempos_falsos = [
        _tiempo_verificacion(CLAVE_PRUEBA, falso) for _ in range(3)
    ]

    relacion = statistics.median(tiempos_reales) / statistics.median(tiempos_falsos)
    # Margen amplio: la comparación es relativa y no depende de la máquina.
    assert 0.4 <= relacion <= 2.5
