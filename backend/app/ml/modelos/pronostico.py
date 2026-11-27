"""Modelo clásico de pronóstico: SARIMAX con fallback a Holt-Winters.

Las librerías de ML se importan dentro de las funciones para que este
módulo se pueda importar sin statsmodels/joblib instalados (la app no
depende de ellas). Sin modelo entrenado, las funciones devuelven None.
"""
from __future__ import annotations

import math
from pathlib import Path

NOMBRE_MODELO = "pronostico_clasico"
ARCHIVO_MODELO = "pronostico_clasico.joblib"
ESTACIONALIDAD = 12
MODELOS_DIR = Path(__file__).resolve().parents[3] / "ml_models"


def entrenar_modelo(serie, horizonte=6, estacional=ESTACIONALIDAD):
    """Entrena el clásico sobre una serie mensual (lista de floats).

    Prueba SARIMAX(1,1,1)x(1,1,1,12) sin tendencia (en la serie de
    ejemplo con tendencia el intercepto post-diferenciación empeora el
    holdout); si falla o la serie es corta usa ExponentialSmoothing
    (Holt-Winters aditivo). Devuelve un artefacto serializable con
    joblib.
    """
    y = [float(v) for v in serie]
    if len(y) < estacional + 2:
        raise ValueError(
            f"serie muy corta: {len(y)} puntos, mínimo {estacional + 2}"
        )

    tipo = "sarimax"
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        resultado = SARIMAX(
            y,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, estacional),
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, maxiter=200)
    except Exception:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        tipo = "holt_winters"
        resultado = ExponentialSmoothing(
            y, trend="add", seasonal="add",
            seasonal_periods=estacional,
        ).fit()

    return {
        "nombre": NOMBRE_MODELO,
        "tipo": tipo,
        "estacional": estacional,
        "historia": y,
        "resultado": resultado,
    }


def predecir(modelo, horizonte=6):
    """Devuelve la lista de pronósticos o None si no hay modelo válido."""
    if not isinstance(modelo, dict) or "resultado" not in modelo:
        return None
    try:
        resultado = modelo["resultado"]
        if hasattr(resultado, "get_forecast"):
            valores = resultado.get_forecast(steps=int(horizonte)).predicted_mean
        elif hasattr(resultado, "forecast"):
            # HoltWintersResults usa forecast(), no get_forecast().
            valores = resultado.forecast(steps=int(horizonte))
        else:
            return None
        return [float(v) for v in valores]
    except Exception:
        return None


def metricas(y_real, y_pred):
    """MAE, RMSE y sMAPE (en %) entre valores reales y pronosticados."""
    pares = [
        (float(r), float(p)) for r, p in zip(y_real, y_pred)
        if r is not None and p is not None
    ]
    n = len(pares)
    if n == 0:
        return {"n": 0, "mae": None, "rmse": None, "smape": None}
    mae = sum(abs(r - p) for r, p in pares) / n
    rmse = math.sqrt(sum((r - p) ** 2 for r, p in pares) / n)
    smape = sum(
        0.0 if abs(r) + abs(p) == 0 else 2 * abs(r - p) / (abs(r) + abs(p))
        for r, p in pares
    ) / n * 100.0
    return {
        "n": n,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "smape": round(smape, 4),
    }


def baseline_mismo_mes_anterior(historia, horizonte, estacional=ESTACIONALIDAD):
    """Pronóstico naïve: mismo mes del año anterior. Sin historia = None."""
    h = [float(v) for v in historia]
    if len(h) < estacional:
        return None
    n = len(h)
    salida = []
    for k in range(1, horizonte + 1):
        idx = n + k - 1 - estacional
        salida.append(h[idx] if idx >= 0 else h[-1])
    return salida


def baseline_media_movil(historia, horizonte, ventana=ESTACIONALIDAD):
    """Pronóstico naïve: media de los últimos `ventana` meses."""
    h = [float(v) for v in historia]
    if not h:
        return None
    base = sum(h[-min(ventana, len(h)):]) / min(ventana, len(h))
    return [base] * int(horizonte)


def guardar_modelo(modelo, directorio=None):
    """Guarda el artefacto en backend/ml_models/ (ignorado por Git)."""
    import joblib

    destino = Path(directorio) if directorio else MODELOS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / ARCHIVO_MODELO
    joblib.dump(modelo, ruta)
    return ruta


def cargar_modelo(ruta):
    """Carga un artefacto joblib; None si no existe o falla."""
    import joblib

    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    try:
        return joblib.load(ruta)
    except Exception:
        return None
