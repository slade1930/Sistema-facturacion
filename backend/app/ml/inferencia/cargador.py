"""Cargador simple de modelos (paso 0; se usa en el paso 4).

Módulo app.ml.inferencia. Equipo ML. Busca en backend/ml_models/ desde __file__:
si no hay archivo, devuelve None. Sin librerías de ML: la app sigue andando.
"""

from pathlib import Path

CARPETA_MODELOS = Path(__file__).resolve().parents[3] / "ml_models"


def cargar_modelo(nombre):
    """Devuelve la ruta si el modelo existe; si no, None sin lanzar error."""
    if not isinstance(nombre, str) or not nombre:
        return None
    ruta = CARPETA_MODELOS / Path(nombre).name
    return ruta if ruta.is_file() else None
