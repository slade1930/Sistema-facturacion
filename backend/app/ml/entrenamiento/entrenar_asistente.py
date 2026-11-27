"""Entrenamiento del asistente (paso 0; se implementa en el paso 3).

Módulo app.ml.entrenamiento. Dueño: Fernando (Módulo 4). Depende de asistente/frases_entrenamiento.py.
Red pequeña local, sin descargar nada ni datos de clientes.
"""
from __future__ import annotations

from app.ml.asistente.frases_entrenamiento import FRASES_ROTULOADAS
from app.ml.modelos import asistente as modelo

EPOCAS = 400
TASA = 0.05


def entrenar_asistente(*, guardar=True, epocas=EPOCAS, tasa=TASA):
    frases = [frase for frase, _ in FRASES_ROTULOADAS]
    etiquetas = [etiqueta for _, etiqueta in FRASES_ROTULOADAS]
    datos = modelo.ajustar(frases, etiquetas, epocas=epocas, tasa=tasa)
    if datos is None or not guardar:
        return datos
    return modelo.guardar(datos)


if __name__ == "__main__":
    ruta = entrenar_asistente()
    print(ruta if ruta else "sin torch: modelo no entrenado")
