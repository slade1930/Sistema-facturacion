"""Asistente de sugerencias (paso 0; se implementa en el paso 3).

Módulo app.ml.modelos. Equipo ML. Depende de los rasgos del paso 2. Sugiere, no decide.
"""
from __future__ import annotations

import pickle
import re
import struct
from datetime import date
from pathlib import Path

from app.ml.asistente import intenciones
from app.ml.asistente.catalogo import INTENCIONES
from app.ml.inferencia.cargador import CARPETA_MODELOS, cargar_modelo

try:
    import torch
except ImportError:
    torch = None

NOMBRE_MODELO = "asistente.pt"
NOMBRE_PUBLICO = "asistente-red-local"
UMBRAL_CONFIANZA = 0.60
OCULTAS = 32
SEMILLA = 20261126


def disponible():
    return torch is not None


def tokenizar(texto):
    return re.findall(r"[a-z0-9]+", intenciones.normalizar(texto))


def vocabulario_desde(frases):
    tokens = set()
    for frase in frases:
        tokens.update(tokenizar(frase))
    return {token: indice for indice, token in enumerate(sorted(tokens))}


def vectorizar(texto, vocabulario):
    vector = [0.0] * len(vocabulario)
    for token in tokenizar(texto):
        indice = vocabulario.get(token)
        if indice is not None:
            vector[indice] += 1.0
    return vector


def _vector(texto, vocabulario):
    vector = vectorizar(texto, vocabulario)
    total = sum(vector) or 1.0
    return [valor / total for valor in vector]


def crear_red(n_entradas, n_salidas=len(INTENCIONES)):
    return torch.nn.Sequential(
        torch.nn.Linear(n_entradas, OCULTAS),
        torch.nn.ReLU(),
        torch.nn.Linear(OCULTAS, n_salidas),
    )


def ajustar(frases, etiquetas, *, epocas=300, tasa=0.05, semilla=SEMILLA):
    if torch is None:
        return None
    frases = list(frases or ())
    etiquetas = list(etiquetas or ())
    if not frases or len(frases) != len(etiquetas):
        return None
    if any(not str(frase).strip() for frase in frases):
        return None
    if any(etiqueta not in INTENCIONES for etiqueta in etiquetas):
        return None
    torch.manual_seed(semilla)
    clases = list(INTENCIONES)
    vocabulario = vocabulario_desde(frases)
    red = crear_red(len(vocabulario), len(clases))
    perdida = torch.nn.CrossEntropyLoss()
    optimizador = torch.optim.Adam(red.parameters(), lr=tasa)
    entradas = torch.tensor(
        [_vector(frase, vocabulario) for frase in frases], dtype=torch.float32
    )
    objetivo = torch.tensor(
        [clases.index(etiqueta) for etiqueta in etiquetas], dtype=torch.long
    )
    red.train()
    for _ in range(epocas):
        optimizador.zero_grad()
        salida = red(entradas)
        valor = perdida(salida, objetivo)
        valor.backward()
        optimizador.step()
    return {"vocabulario": vocabulario, "clases": clases, "estado": red.state_dict()}


def guardar(datos, nombre=NOMBRE_MODELO):
    if torch is None or datos is None:
        return None
    ruta = CARPETA_MODELOS / (Path(nombre).name if nombre else NOMBRE_MODELO)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    torch.save(datos, ruta)
    return ruta


def predecir(pregunta, nombre=NOMBRE_MODELO, hoy: date | None = None):
    if torch is None:
        return None
    texto = intenciones.normalizar(pregunta)
    if not texto:
        return None
    ruta = cargar_modelo(nombre)
    if ruta is None:
        return None
    try:
        datos = torch.load(ruta, map_location="cpu", weights_only=True)
        vocabulario = datos["vocabulario"]
        if not any(token in vocabulario for token in tokenizar(texto)):
            return None
        clases = datos["clases"]
        red = crear_red(len(vocabulario), len(clases))
        red.load_state_dict(datos["estado"])
        red.eval()
        with torch.no_grad():
            entrada = torch.tensor(
                [_vector(pregunta, vocabulario)], dtype=torch.float32
            )
            probabilidades = torch.softmax(red(entrada), dim=-1)[0]
        confianza, indice = torch.max(probabilidades, dim=0)
        valor = float(confianza)
        nombre_intencion = clases[int(indice)]
        if valor < UMBRAL_CONFIANZA or nombre_intencion not in INTENCIONES:
            return None
        parametros = intenciones.extraer_parametros(texto, hoy)
        if intenciones.FECHA_INVALIDA in parametros:
            return None
        return intenciones.Intencion(nombre_intencion, valor, parametros)
    except (
        OSError,
        EOFError,
        struct.error,
        pickle.UnpicklingError,
        AttributeError,
        KeyError,
        IndexError,
        ValueError,
        RuntimeError,
        TypeError,
    ):
        return None
