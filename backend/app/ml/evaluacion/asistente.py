"""Evaluación del asistente (paso 0; se implementa en el paso 4).

Módulo app.ml.evaluacion. Dueño: Luis (Módulo 4). Depende de modelos/asistente.py.
Compara la red pequeña contra las palabras clave; sin datos reales.
"""
from __future__ import annotations

import json

from app.ml.asistente.frases_entrenamiento import FRASES_VALIDACION
from app.ml.asistente.intenciones import clasificar
from app.ml.modelos import asistente as modelo


def _metricas(aciertos, total):
    return {
        "aciertos": aciertos,
        "total": total,
        "precision": round(aciertos / total, 4) if total else 0.0,
    }


def evaluar_asistente(
    frases=FRASES_VALIDACION,
    *,
    nombre_modelo=modelo.NOMBRE_MODELO,
    hoy=None,
):
    frases = list(frases)
    evaluado = modelo.disponible() and modelo.cargar_modelo(nombre_modelo) is not None
    aciertos_base = 0
    aciertos_modelo = 0
    detalle = []
    predicciones = []
    for frase, esperado in frases:
        base = clasificar(frase, hoy=hoy)
        prediccion = modelo.predecir(frase, nombre_modelo, hoy=hoy) if evaluado else None
        predicciones.append(prediccion)
        nombre_base = base.nombre if base else None
        nombre_predicho = prediccion.nombre if prediccion else None
        aciertos_base += nombre_base == esperado
        aciertos_modelo += nombre_predicho == esperado
        detalle.append(
            {
                "frase": frase,
                "esperado": esperado,
                "linea_base": nombre_base,
                "parametros_linea_base": base.parametros if base else None,
                "modelo": nombre_predicho,
                "parametros_modelo": prediccion.parametros if prediccion else None,
                "confianza": prediccion.confianza if prediccion else None,
            }
        )
    total = len(frases)
    if evaluado and predicciones and not any(predicciones):
        evaluado = False
    return {
        "evaluado": evaluado,
        "modelo": modelo.NOMBRE_PUBLICO if evaluado else None,
        "linea_base": _metricas(aciertos_base, total),
        "red_local": _metricas(aciertos_modelo, total) if evaluado else None,
        "detalle": detalle,
    }


if __name__ == "__main__":
    print(json.dumps(evaluar_asistente(), ensure_ascii=False, indent=2))
