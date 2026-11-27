"""Evaluación del pronóstico con separación temporal estricta.

Módulo app.ml.evaluacion. Dueño: Joan (Módulo 2).
Nunca baraja la serie: los últimos `meses_prueba` puntos son el holdout
y el modelo solo entrena con los anteriores. Compara contra las líneas
base "mismo mes del año anterior" y "media móvil" con MAE, RMSE y sMAPE.

Las librerías pesadas (statsmodels, torch) se importan dentro de las
funciones: este módulo se importa en cualquier entorno.
"""
from __future__ import annotations


def _split_temporal(serie, meses_prueba):
    y = [float(v) for v in serie]
    if len(y) <= meses_prueba:
        raise ValueError(
            f"serie muy corta: {len(y)} puntos, mínimo {meses_prueba + 1}"
        )
    return y[:-meses_prueba], y[-meses_prueba:]


def _evaluar_clasico(train, test, horizonte, estacional=12):
    from app.ml.modelos import pronostico as pm

    modelo = pm.entrenar_modelo(train, horizonte=horizonte,
                                estacional=estacional)
    pred = pm.predecir(modelo, horizonte=horizonte)
    return pred, pm.metricas(test, pred) if pred else None


def _evaluar_lstm(train, test, horizonte, epocas=80, semilla=20261126):
    """Devuelve (prediccion, metricas) o None si torch no está disponible."""
    try:
        import torch  # noqa: F401
    except ImportError:
        return None
    from app.ml.modelos import pronostico as pm
    from app.ml.modelos import pronostico_lstm as lstm

    modelo = lstm.entrenar_lstm(
        train, horizonte=horizonte, epocas=epocas, semilla=semilla
    )
    pred = lstm.predecir(modelo, horizonte=horizonte)
    return pred, pm.metricas(test, pred) if pred else None


def evaluar_serie(periodos, serie, meses_prueba=6, horizonte=6,
                  con_lstm=True, epocas_lstm=80, estacional=12):
    """Evalúa los modelos sobre el holdout temporal de la serie.

    Devuelve {"periodos_test", "y_test", "predicciones", "metricas"}.
    `predicciones` y `metricas` usan las claves "clasico", "lstm" (solo
    si torch está instalado) y los baselines "mismo_mes_anterior" y
    "media_movil".
    """
    from app.ml.modelos import pronostico as pm

    train, test = _split_temporal(serie, meses_prueba)
    periodos_test = list(periodos)[-meses_prueba:]

    pred_clasico, met_clasico = _evaluar_clasico(
        train, test, horizonte, estacional=estacional
    )

    prediccion = {"clasico": pred_clasico}
    metricas = {"clasico": met_clasico}

    if con_lstm:
        res_lstm = _evaluar_lstm(
            train, test, horizonte, epocas=epocas_lstm
        )
        if res_lstm is not None:
            pred_lstm, met_lstm = res_lstm
            prediccion["lstm"] = pred_lstm
            metricas["lstm"] = met_lstm

    pred_na = pm.baseline_mismo_mes_anterior(
        train, horizonte, estacional=estacional
    )
    pred_mm = pm.baseline_media_movil(train, horizonte,
                                      ventana=estacional)
    prediccion["mismo_mes_anterior"] = pred_na
    prediccion["media_movil"] = pred_mm
    metricas["mismo_mes_anterior"] = pm.metricas(test, pred_na)
    metricas["media_movil"] = pm.metricas(test, pred_mm)

    return {
        "periodos_test": periodos_test,
        "y_test": test,
        "predicciones": prediccion,
        "metricas": metricas,
    }
