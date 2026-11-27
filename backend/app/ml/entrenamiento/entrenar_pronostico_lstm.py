"""Entrenamiento de la LSTM de pronóstico (PyTorch CPU).

Mismo contrato que entrenar_pronostico.py: separación TEMPORAL
estricta (holdout = últimos `meses_prueba` meses), métricas contra
'mmismo mes del año anterior' y 'media móvil' con MAE/RMSE/sMAPE, y
modelo guardado en backend/ml_models/ (fuera de Git).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.modelos import pronostico_lstm as lstm  # noqa: E402

ESTACIONAL = 12


def cargar_serie_total(directorio):
    """Serie mensual total (solo facturas emitidas) desde los CSV."""
    from app.ml.datasets import generar_datos as gd

    datos = gd.cargar_dataset_ml(directorio)
    acum = {}
    for factura in datos["facturas"]:
        if factura.get("estado") == "anulada":
            continue
        mes = str(factura.get("fecha"))[:7]
        acum[mes] = acum.get(mes, 0.0) + float(factura.get("total") or 0)
    periodos = sorted(acum)
    return periodos, [round(acum[p], 2) for p in periodos]


def _metricas(y_real, y_pred):
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
    return {"n": n, "mae": round(mae, 4), "rmse": round(rmse, 4),
            "smape": round(smape, 4)}


def _baseline_mismo_mes_anterior(historia, horizonte, estacional=ESTACIONAL):
    h = [float(v) for v in historia]
    if len(h) < estacional:
        return None
    n = len(h)
    salida = []
    for k in range(1, horizonte + 1):
        idx = n + k - 1 - estacional
        salida.append(h[idx] if idx >= 0 else h[-1])
    return salida


def _baseline_media_movil(historia, horizonte, ventana=ESTACIONAL):
    h = [float(v) for v in historia]
    if not h:
        return None
    base = sum(h[-min(ventana, len(h)):]) / min(ventana, len(h))
    return [base] * int(horizonte)


def evaluar_split_temporal_lstm(periodos, serie, meses_prueba=6,
                                epocas=80, ventana=lstm.VENTANA,
                                semilla=20261126):
    """Entrena en train y evalúa en test (temporal, nunca aleatorio)."""
    if len(serie) <= meses_prueba:
        raise ValueError("serie demasiado corta para el split temporal")
    corte = len(serie) - meses_prueba
    train, test = serie[:corte], serie[corte:]
    periodos_test = periodos[corte:]

    modelo = lstm.entrenar_lstm(
        train, horizonte=meses_prueba, ventana=ventana,
        epocas=epocas, semilla=semilla,
    )
    pred = lstm.predecir(modelo, horizonte=meses_prueba)

    return {
        "periodos_train": periodos[:corte],
        "periodos_test": periodos_test,
        "y_test": test,
        "modelo": modelo,
        "prediccion": pred,
        "metricas": {
            "lstm": _metricas(test, pred) if pred else None,
            "mismo_mes_anterior": _metricas(
                test, _baseline_mismo_mes_anterior(train, meses_prueba)
            ),
            "media_movil": _metricas(
                test, _baseline_media_movil(train, meses_prueba)
            ),
        },
    }


def entrenar(directorio=None, meses_prueba=6, epocas=80, semilla=20261126,
             directorio_modelos=None):
    """Pipeline completo: CSV -> features -> split -> métricas -> LSTM."""
    from app.ml.datasets import generar_datos as gd

    directorio = directorio or gd.SALIDA
    periodos, serie = cargar_serie_total(directorio)
    resultado = evaluar_split_temporal_lstm(
        periodos, serie, meses_prueba=meses_prueba, epocas=epocas,
        semilla=semilla,
    )

    ruta = None
    if directorio_modelos is not None:
        # El artefacto final usa toda la serie para pronosticar a futuro.
        modelo_full = lstm.entrenar_lstm(
            serie, horizonte=lstm.HORIZONTE, epocas=epocas, semilla=semilla,
        )
        ruta = lstm.guardar_modelo(modelo_full, directorio_modelos)

    resultado["ruta_modelo"] = str(ruta) if ruta else None
    return resultado


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=None)
    parser.add_argument("--meses-prueba", type=int, default=6)
    parser.add_argument("--epocas", type=int, default=80)
    parser.add_argument("--semilla", type=int, default=20261126)
    parser.add_argument("--sin-guardar", action="store_true")
    args = parser.parse_args(argv)

    res = entrenar(
        directorio=args.datos,
        meses_prueba=args.meses_prueba,
        epocas=args.epocas,
        semilla=args.semilla,
        directorio_modelos=None if args.sin_guardar else lstm.MODELOS_DIR,
    )
    print(json.dumps({
        "periodos_test": res["periodos_test"],
        "metricas": res["metricas"],
        "ruta_modelo": res["ruta_modelo"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
