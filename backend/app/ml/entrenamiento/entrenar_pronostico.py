"""Entrenamiento del pronóstico clásico (SARIMAX/Holt-Winters).

Separación TEMPORAL estricta: los últimos `meses_prueba` meses de la
serie son el holdout; el modelo solo ve los meses anteriores. Nunca
se baraja ni se parte al azar.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.datasets import generar_datos as gd  # noqa: E402
from app.ml.features import pronostico as features  # noqa: E402
from app.ml.modelos import pronostico as modelos  # noqa: E402


def cargar_serie_total(directorio):
    """Serie mensual total (solo facturas emitidas) desde los CSV."""
    datos = gd.cargar_dataset_ml(directorio)
    matriz = features.matriz_mensual(
        datos["facturas"], datos["lineas_factura"], nivel="total"
    )
    clave = matriz["claves"][0] if matriz["claves"] else "total"
    return matriz["periodos"], matriz["valores"].get(clave, [])


def evaluar_split_temporal(periodos, serie, meses_prueba=6):
    """Entrena en train y compara contra test con métricas y baselines."""
    if len(serie) <= meses_prueba:
        raise ValueError("serie demasiado corta para el split temporal")
    corte = len(serie) - meses_prueba
    train, test = serie[:corte], serie[corte:]
    periodos_test = periodos[corte:]

    modelo = modelos.entrenar_modelo(train, horizonte=meses_prueba)
    pred = modelos.predecir(modelo, horizonte=meses_prueba)

    return {
        "periodos_train": periodos[:corte],
        "periodos_test": periodos_test,
        "y_test": test,
        "modelo": modelo,
        "prediccion": pred,
        "metricas": {
            "modelo": modelos.metricas(test, pred) if pred else None,
            "mismo_mes_anterior": modelos.metricas(
                test, modelos.baseline_mismo_mes_anterior(train, meses_prueba)
            ),
            "media_movil": modelos.metricas(
                test, modelos.baseline_media_movil(train, meses_prueba)
            ),
        },
    }


def entrenar(directorio=gd.SALIDA, meses_prueba=6, directorio_modelos=None):
    """Pipeline completo: CSV -> features -> split -> métricas -> modelo."""
    periodos, serie = cargar_serie_total(directorio)
    resultado = evaluar_split_temporal(periodos, serie, meses_prueba)

    ruta = None
    if directorio_modelos is not None:
        # El artefacto final usa toda la serie para pronosticar a futuro.
        modelo_full = modelos.entrenar_modelo(serie, horizonte=6)
        ruta = modelos.guardar_modelo(modelo_full, directorio_modelos)

    resultado["ruta_modelo"] = str(ruta) if ruta else None
    return resultado


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=gd.SALIDA)
    parser.add_argument("--meses-prueba", type=int, default=6)
    parser.add_argument("--sin-guardar", action="store_true")
    args = parser.parse_args(argv)

    res = entrenar(
        directorio=args.datos,
        meses_prueba=args.meses_prueba,
        directorio_modelos=None if args.sin_guardar else modelos.MODELOS_DIR,
    )
    print(json.dumps({
        "periodos_test": res["periodos_test"],
        "metricas": res["metricas"],
        "ruta_modelo": res["ruta_modelo"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
