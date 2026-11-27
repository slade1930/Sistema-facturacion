"""Evaluación de anomalías: reglas vs Isolation Forest contra las etiquetas.

Precisión, recall y F1. Las etiquetas sólo se usan para elegir el umbral
y medir: nunca entrenan el modelo. Sugiere, no decide el estado.
"""
from __future__ import annotations

import json

from app.ml.datasets import generar_datos
from app.ml.entrenamiento.entrenar_anomalias import rasgos_desde_filas
from app.ml.modelos import anomalias as modelo
from app.ml.reglas.anomalias import evaluar_factura

UMBRAL_REGLAS = 20  # cualquier regla que salta ya sugiere revisión
FRACCION_CALIBRACION = 0.6  # 60% para fijar el umbral, 40% sin ver para medir


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


def dividir_etiquetas(etiquetas, fraccion=FRACCION_CALIBRACION):
    """Separa etiquetas en calibración y validación, por id y sin azar.

    El umbral se ajusta sólo con calibración; las métricas se miden con
    validación, que el ajuste nunca vio.
    """
    ids = sorted({int(fid) for fid in etiquetas})
    if len(ids) < 2:
        return set(ids), set()
    corte = max(1, min(len(ids) - 1, round(len(ids) * fraccion)))
    return set(ids[:corte]), set(ids[corte:])


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
    calibracion, validacion = dividir_etiquetas(reales)
    # Con umbral explícito no hay ajuste: se mide sobre todas las etiquetas.
    objetivo = validacion if umbral is None else reales
    sin_modelo = {
        "evaluado": False,
        "modelo": None,
        "total": len(rasgos),
        "etiquetadas": len(objetivo),
        "calibracion": 0,
        "umbral": modelo.UMBRAL_REVISION,
        "reglas": None,
        "isolation_forest": None,
    }
    datos = modelo.cargar(nombre)
    if datos is None or not rasgos:
        return sin_modelo

    puntajes = []
    for fila in rasgos:
        try:
            puntaje = modelo.puntaje_con(datos, fila)
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            return sin_modelo
        puntajes.append((fila.factura_id, round(puntaje, 4)))

    umbral_final = (
        elegir_umbral(puntajes, calibracion) if umbral is None else float(umbral)
    )
    # Lo que se usó para calibrar no se cuenta como falso positivo al medir.
    excluidas = calibracion if umbral is None else set()
    predichos_modelo = {
        fid for fid, puntaje in puntajes
        if fid not in excluidas and puntaje >= umbral_final
    }
    predichos_reglas = {
        fila.factura_id
        for fila in rasgos
        if fila.factura_id not in excluidas
        and evaluar_factura(fila, rasgos).puntaje >= UMBRAL_REGLAS
    }

    resultado = {
        "evaluado": True,
        "modelo": modelo.NOMBRE_PUBLICO,
        "total": len(rasgos),
        "etiquetadas": len(objetivo),
        "calibracion": len(calibracion) if umbral is None else 0,
        "umbral": round(umbral_final, 4),
        "reglas": metricas(predichos_reglas, objetivo),
        "isolation_forest": metricas(predichos_modelo, objetivo),
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
    rasgos = rasgos_desde_filas(facturas)
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
