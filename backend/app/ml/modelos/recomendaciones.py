"""Autoencoder de recomendaciones (Módulo 3).

Modelo local en PyTorch CPU sobre la matriz cliente-producto. Aprende a
reconstruir la cesta de cada cliente y usa esa reconstrucción para
sugerir productos que el cliente aún no tiene. Siempre compite contra
la línea base "más vendidos": el ML sugiere, nunca decide.

Las librerías pesadas se importan dentro de las funciones para que la
app siga arrancando sin torch. Sin artefacto, `recomendar()` devuelve
None y el endpoint cae a las reglas.
"""
from __future__ import annotations

import random
from pathlib import Path

NOMBRE_MODELO = "recomendaciones_autoencoder"
ARCHIVO_MODELO = "recomendaciones.pt"
MODELOS_DIR = Path(__file__).resolve().parents[3] / "ml_models"
SEMILLA = 20261126
OCULTAS = 16
EPOCAS = 120


def disponible() -> bool:
    """¿Está torch instalado? No descarga nada ni rompe si falta."""
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def _construir_red(torch, num_productos: int, ocultas: int):
    return torch.nn.Sequential(
        torch.nn.Linear(num_productos, ocultas),
        torch.nn.ReLU(),
        torch.nn.Linear(ocultas, num_productos),
        torch.nn.Sigmoid(),
    )


def entrenar_autoencoder(
    matriz,
    *,
    ocultas: int = OCULTAS,
    epocas: int = EPOCAS,
    semilla: int = SEMILLA,
    tasa_aprendizaje: float = 0.01,
):
    """Entrena sobre una matriz cliente x producto (DataFrame o similar).

    Devuelve un artefacto serializable con la lista de productos, el
    `state_dict` y la semilla. Sin torch, sin datos o con menos de dos
    clientes/productos devuelve None. Nunca lanza hacia la app.
    """
    try:
        import torch
    except ImportError:
        return None

    if matriz is None or getattr(matriz, "empty", True):
        return None
    productos = [int(columna) for columna in matriz.columns]
    num_clientes = len(matriz.index)
    if len(productos) < 2 or num_clientes < 2:
        return None

    try:
        valores = matriz.fillna(0).to_numpy(dtype="float32")
    except Exception:
        return None

    torch.manual_seed(semilla)
    random.seed(semilla)

    entradas = torch.clamp(torch.tensor(valores, dtype=torch.float32), 0.0, 1.0)
    red = _construir_red(torch, len(productos), int(ocultas))
    optimizador = torch.optim.Adam(red.parameters(), lr=float(tasa_aprendizaje))
    perdida_fn = torch.nn.BCELoss()

    red.train()
    for _ in range(int(epocas)):
        optimizador.zero_grad()
        perdida = perdida_fn(red(entradas), entradas)
        perdida.backward()
        optimizador.step()

    return {
        "nombre": NOMBRE_MODELO,
        "tipo": "autoencoder",
        "productos": productos,
        "ocultas": int(ocultas),
        "epocas": int(epocas),
        "semilla": int(semilla),
        "clientes": num_clientes,
        "estado": red.state_dict(),
    }


def recomendar(modelo, productos_en_cesta, n: int = 5, excluir=None):
    """Top-n desde la reconstrucción de la cesta actual.

    `productos_en_cesta` son los ids que el cliente ya tiene. Nunca se
    recomienda lo que ya está ni lo que llegue en `excluir` (inactivos,
    por ejemplo). Devuelve la misma forma de las reglas para que el
    endpoint pueda caer a la línea base sin cambiar el contrato.
    """
    if (
        not isinstance(modelo, dict)
        or modelo.get("tipo") != "autoencoder"
        or not modelo.get("productos")
        or "estado" not in modelo
    ):
        return None
    try:
        import torch

        productos = [int(p) for p in modelo["productos"]]
        posiciones = {pid: idx for idx, pid in enumerate(productos)}
        entradas = torch.zeros((1, len(productos)), dtype=torch.float32)
        for pid in productos_en_cesta or []:
            idx = posiciones.get(int(pid))
            if idx is not None:
                entradas[0, idx] = 1.0

        red = _construir_red(
            torch, len(productos), int(modelo.get("ocultas", OCULTAS))
        )
        red.load_state_dict(modelo["estado"])
        red.eval()
        with torch.no_grad():
            puntajes = red(entradas)[0].tolist()

        ya = {int(p) for p in (productos_en_cesta or [])}
        excluidos = ya | {int(p) for p in (excluir or [])}
        candidatos = [
            (float(puntaje), pid)
            for pid, puntaje in zip(productos, puntajes)
            if pid not in excluidos
        ]
        candidatos.sort(key=lambda item: (-item[0], item[1]))
        return [
            {
                "producto_id": pid,
                "puntaje": round(puntaje, 6),
                "fuente": "autoencoder",
            }
            for puntaje, pid in candidatos[: int(n)]
        ]
    except Exception:
        return None


def predecir(modelo, productos_en_cesta, n: int = 5, excluir=None):
    """Alias de `recomendar` para el contrato de inferencia del ML."""
    return recomendar(modelo, productos_en_cesta, n=n, excluir=excluir)


def guardar_modelo(modelo, directorio=None):
    """Guarda el artefacto en `backend/ml_models/` (fuera de Git)."""
    try:
        import torch
    except ImportError:
        return None
    if not isinstance(modelo, dict) or modelo.get("tipo") != "autoencoder":
        return None
    destino = Path(directorio) if directorio else MODELOS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / ARCHIVO_MODELO
    torch.save(modelo, ruta)
    return ruta


def cargar_modelo(ruta):
    """Carga el artefacto; None si no existe o está corrupto."""
    try:
        import torch
    except ImportError:
        return None
    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    try:
        artefacto = torch.load(ruta, map_location="cpu", weights_only=True)
    except Exception:
        try:
            artefacto = torch.load(ruta, map_location="cpu", weights_only=False)
        except Exception:
            return None
    if not isinstance(artefacto, dict) or artefacto.get("tipo") != "autoencoder":
        return None
    return artefacto
