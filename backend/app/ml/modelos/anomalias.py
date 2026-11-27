"""Isolation Forest en Python puro para anomalías en facturas.

Sin librerías nuevas: usa random y pickle, guarda en backend/ml_models/.
Sugiere revisión, nunca cambia el estado de la factura.
"""
from __future__ import annotations

import math
import pickle
import random
from dataclasses import dataclass
from pathlib import Path

from app.ml.features.anomalias import RasgosFactura
from app.ml.inferencia.cargador import CARPETA_MODELOS as RUTA_MODELOS

CARPETA_MODELOS = RUTA_MODELOS
NOMBRE_MODELO = "anomalias.pkl"
NOMBRE_PUBLICO = "anomalias-isolation-forest"
NOMBRES_RASGOS = ("total", "descuento", "anulada", "mes")
SEMILLA = 20261126
N_ARBOLES = 100
UMBRAL_REVISION = 0.65  # lo ajusta evaluacion/anomalias.py con las etiquetas
GAMMA = 0.5772156649015329


@dataclass(frozen=True)
class PrediccionAnomalia:
    puntaje: float       # 0 a 1, más alto = más raro
    en_revision: bool    # sugerencia, no decide el estado


def vectorizar(rasgos: RasgosFactura) -> list[float]:
    """Deja los rasgos en un vector numérico fijo, sin tocar Decimal."""
    return [
        float(rasgos.total),
        float(rasgos.descuento_max_pct),
        1.0 if rasgos.anulada else 0.0,
        float(rasgos.fecha.month),
    ]


def _longitud_c(n):
    """Path promedio esperado en un árbol aleatorio de n muestras."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    return 2 * (math.log(n - 1) + GAMMA) - 2 * (n - 1) / n


def _construir_arbol(filas, rng, profundidad, maxima):
    nodo = {"n": len(filas)}
    if len(filas) <= 1 or profundidad >= maxima:
        return nodo
    ejes = [
        i for i in range(len(NOMBRES_RASGOS))
        if min(fila[i] for fila in filas) < max(fila[i] for fila in filas)
    ]
    if not ejes:
        return nodo
    eje = rng.choice(ejes)
    corte = rng.uniform(min(fila[eje] for fila in filas), max(fila[eje] for fila in filas))
    izquierda = [fila for fila in filas if fila[eje] < corte]
    derecha = [fila for fila in filas if fila[eje] >= corte]
    if not izquierda or not derecha:
        return nodo
    nodo.update(
        eje=eje,
        corte=corte,
        izquierda=_construir_arbol(izquierda, rng, profundidad + 1, maxima),
        derecha=_construir_arbol(derecha, rng, profundidad + 1, maxima),
    )
    return nodo


def _profundidad(fila, nodo, profundidad=0):
    if "eje" not in nodo:
        return profundidad + _longitud_c(nodo["n"])
    if fila[nodo["eje"]] < nodo["corte"]:
        return _profundidad(fila, nodo["izquierda"], profundidad + 1)
    return _profundidad(fila, nodo["derecha"], profundidad + 1)


def entrenar(rasgos, *, n_arboles=N_ARBOLES, semilla=SEMILLA):
    """Entrena sin etiquetas; devuelve None si no hay muestras."""
    filas = [vectorizar(rasgos_fila) for rasgos_fila in rasgos]
    if not filas:
        return None
    rng = random.Random(semilla)
    maxima = max(1, math.ceil(math.log2(len(filas))))
    return {
        "version": 1,
        "semilla": semilla,
        "n": len(filas),
        "rasgos": list(NOMBRES_RASGOS),
        "arboles": [
            _construir_arbol(filas, rng, 0, maxima) for _ in range(n_arboles)
        ],
    }


def guardar(datos, nombre=NOMBRE_MODELO):
    """Guarda el modelo con pickle dentro de backend/ml_models/."""
    if not datos:
        return None
    ruta = Path(CARPETA_MODELOS) / (Path(nombre).name if nombre else NOMBRE_MODELO)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("wb") as archivo:
        pickle.dump(datos, archivo, protocol=pickle.HIGHEST_PROTOCOL)
    return ruta


def cargar(nombre=NOMBRE_MODELO):
    """Lee el modelo propio; archivo raro o corrupto devuelve None."""
    ruta = Path(CARPETA_MODELOS) / (Path(nombre).name if nombre else NOMBRE_MODELO)
    if not ruta.is_file():
        return None
    try:
        with ruta.open("rb") as archivo:
            datos = pickle.load(archivo)
    except (
        OSError,
        EOFError,
        pickle.UnpicklingError,
        AttributeError,
        ValueError,
        TypeError,
        ImportError,
    ):
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("arboles"), list):
        return None
    if not datos["arboles"]:
        return None
    return datos


def disponible(nombre=NOMBRE_MODELO):
    return cargar(nombre) is not None


def puntaje_con(datos, rasgos):
    """Puntaje con un modelo ya cargado, para evaluar sin leer el disco."""
    arboles = datos["arboles"]
    fila = vectorizar(rasgos)
    normalizacion = _longitud_c(datos["n"])
    if normalizacion <= 0:
        return 0.0
    promedio = sum(_profundidad(fila, arbol) for arbol in arboles) / len(arboles)
    return 2 ** (-promedio / normalizacion)


def predecir(rasgos, nombre=NOMBRE_MODELO, umbral=UMBRAL_REVISION):
    """Sin modelo o con uno corrupto devuelve None; la app sigue andando."""
    datos = cargar(nombre)
    if datos is None:
        return None
    try:
        puntaje = puntaje_con(datos, rasgos)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return None
    return PrediccionAnomalia(round(puntaje, 4), puntaje >= umbral)
