"""Evaluación de anomalías: reglas vs Isolation Forest contra las etiquetas.

Precisión, recall y F1. Las etiquetas sólo se usan para elegir el umbral
y medir: nunca entrenan el modelo. Sugiere, no decide el estado.
"""
from __future__ import annotations

import json

from app.ml.datasets import generar_datos
from app.ml.entrenamiento.entrenar_anomalias import rasgos_desde_fila
from app.ml.modelos import anomalias as modelo
from app.ml.reglas.anomalias import evaluar_factura

UMBRAL_REGLAS = 20  # cualquier regla que salta ya sugiere revisión


def metricas(predichos, reales):
    """Métricas binarias sobre ids de factura."""
    predichos, reales = set(predichos), set(reales)
    tp = len(predichos & reales)
    fp = len(predichos - reales)
    fn = len(reales - predichos)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def elegir_umbral(puntajes, reales):
    """Umbral con mejor F1; en empate gana el más alto (menos ruido)."""
    if not puntajes or not reales:
        return modelo.UMBRAL_REVISION
    mejor = modelo.UMBRAL_REVISION
    mejor_f1 = -1.0
    candidatos = sorted({0.0} | {round(puntaje, 4) for _, puntaje in puntajes})
    for umbral in candidatos:
        predichos = {fid for fid, puntaje in puntajes if puntaje >= umbral}
        f1 = metricas(predichos, reales)["f1"]
        if f1 > mejor_f1 or (f1 == mejor_f1 and umbral > mejor):
            mejor, mejor_f1 = umbral, f1
    return round(mejor, 4)


def evaluar_anomalias(
    rasgos,
    etiquetas=None,
    *,
    nombre=modelo.NOMBRE_MODELO,
    umbral=None,
    incluir_detalle=False,
):
    """Compara las reglas contra el modelo; sin modelo devuelve evaluado=False."""
    rasgos = list(rasgos)
    reales = {int(fid) for fid in etiquetas or ()}
    datos = modelo.cargar(nombre)
    if datos is None or not rasgos:
        return {
            "evaluado": False,
            "modelo": None,
            "total": len(rasgos),
            "etiquetadas": len(reales),
            "umbral": modelo.UMBRAL_REVISION,
            "reglas": None,
            "isolation_forest": None,
        }

    puntajes = []
    for fila in rasgos:
        try:
            puntaje = modelo.puntaje_con(datos, fila)
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            return {
                "evaluado": False,
                "modelo": None,
                "total": len(rasgos),
                "etiquetadas": len(reales),
                "umbral": modelo.UMBRAL_REVISION,
                "reglas": None,
                "isolation_forest": None,
            }
        puntajes.append((fila.factura_id, round(puntaje, 4)))

    umbral_final = (
        elegir_umbral(puntajes, reales) if umbral is None else float(umbral)
    )
    predichos_modelo = {fid for fid, puntaje in puntajes if puntaje >= umbral_final}
    predichos_reglas = {
        fila.factura_id
        for fila in rasgos
        if evaluar_factura(fila, rasgos).puntaje >= UMBRAL_REGLAS
    }

    resultado = {
        "evaluado": True,
        "modelo": modelo.NOMBRE_PUBLICO,
        "total": len(rasgos),
        "etiquetadas": len(reales),
        "umbral": round(umbral_final, 4),
        "reglas": metricas(predichos_reglas, reales),
        "isolation_forest": metricas(predichos_modelo, reales),
    }
    if incluir_detalle:
        resultado["detalle"] = [
            {
                "factura_id": fid,
                "etiquetada": fid in reales,
                "puntaje": puntaje,
                "modelo_revision": fid in predichos_modelo,
                "reglas_revision": fid in predichos_reglas,
            }
            for fid, puntaje in puntajes
        ]
    return resultado


def evaluar_desde_csv(
    directorio=generar_datos.SALIDA,
    nombre=modelo.NOMBRE_MODELO,
    umbral=None,
    incluir_detalle=False,
):
    """Evalúa contra las 55 etiquetas de los CSV generados."""
    facturas, etiquetas = generar_datos.leer_dataset_csv(directorio)
    rasgos = [rasgos_desde_fila(fila) for fila in facturas]
    reales = {
        int(etiqueta["factura_id"])
        for etiqueta in etiquetas
        if str(etiqueta.get("factura_id", "")).isdigit()
    }
    return evaluar_anomalias(
        rasgos,
        reales,
        nombre=nombre,
        umbral=umbral,
        incluir_detalle=incluir_detalle,
    )


if __name__ == "__main__":
    print(json.dumps(evaluar_desde_csv(), ensure_ascii=False, indent=2))
