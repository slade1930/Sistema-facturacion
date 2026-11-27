"""Cargador simple de modelos (paso 0; se usa en el paso 4).

Módulo app.ml.inferencia. Equipo ML. Busca en backend/ml_models/ desde __file__:
si no hay archivo, devuelve None. Sin librerías de ML: la app sigue andando.
"""

from pathlib import Path

CARPETA_MODELOS = Path(__file__).resolve().parents[3] / "ml_models"


def cargar_modelo(nombre, directorio=None):
    """Devuelve la ruta si el modelo existe; si no, None sin lanzar error."""
    if not isinstance(nombre, str) or not nombre:
        return None
    base = Path(directorio) if directorio else CARPETA_MODELOS
    ruta = base / Path(nombre).name
    return ruta if ruta.is_file() else None


def cargar_artefacto(nombre, directorio=None):
    """Carga el modelo entrenado (.joblib o .pt) o None.

    Elige el cargador según la extensión; las librerías pesadas se
    importan de forma diferida dentro de cada módulo de modelos.
    """
    ruta = cargar_modelo(nombre, directorio)
    if ruta is None:
        return None
    sufijo = ruta.suffix.lower()
    try:
        if sufijo == ".pt":
            from app.ml.modelos import pronostico_lstm

            return pronostico_lstm.cargar_modelo(ruta)
        if sufijo in (".joblib", ".pkl"):
            from app.ml.modelos import pronostico

            return pronostico.cargar_modelo(ruta)
    except Exception:
        return None
    return None
