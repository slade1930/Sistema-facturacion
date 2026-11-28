"""Entrenamiento de recomendaciones (paso 0; se implementa en el paso 3).

Módulo app.ml.entrenamiento. Equipo ML. Depende del modelo y los datos marcados.
"""
"""Entrenamiento del autoencoder de recomendaciones (Módulo 3, makirvy).

Carga los datos de ejemplo (CSV si existen o dataset en memoria),
construye la matriz cliente-producto y guarda `recomendaciones.pt` en
`backend/ml_models/` (fuera de Git).

Uso:
  python -m app.ml.entrenamiento.entrenar_recomendaciones
  python -m app.ml.entrenamiento.entrenar_recomendaciones --epocas 150
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.datasets.generar_datos import (  # noqa: E402
    SALIDA as DATOS_DIR,
    cargar_dataset_ml,
    construir_dataset,
)
from app.ml.features.recomendaciones import (  # noqa: E402
    cestas_desde_dataset,
    matriz_cliente_producto,
)
from app.ml.modelos.recomendaciones import (  # noqa: E402
    EPOCAS,
    MODELOS_DIR,
    OCULTAS,
    SEMILLA,
    disponible,
    entrenar_autoencoder,
    guardar_modelo,
)


def cargar_o_construir_dataset(directorio_datos: Path | None = None):
    """Usa los CSV generados si existen; si no, construye el dataset de ejemplo."""
    carpeta = Path(directorio_datos) if directorio_datos else DATOS_DIR
    if (carpeta / "facturas_ejemplo.csv").is_file():
        return cargar_dataset_ml(carpeta)
    return construir_dataset()


def entrenar_desde_dataset(
    dataset,
    *,
    directorio_salida: Path | None = None,
    ocultas: int = OCULTAS,
    epocas: int = EPOCAS,
    semilla: int = SEMILLA,
    tasa_aprendizaje: float = 0.01,
):
    """Entrena el autoencoder a partir de un dataset y guarda el `.pt`."""
    if not disponible():
        return None, None

    cestas = cestas_desde_dataset(dataset)
    matriz = matriz_cliente_producto(cestas, valor="presencia")
    modelo = entrenar_autoencoder(
        matriz,
        ocultas=ocultas,
        epocas=epocas,
        semilla=semilla,
        tasa_aprendizaje=tasa_aprendizaje,
    )
    if modelo is None:
        return None, None

    ruta = guardar_modelo(modelo, directorio=directorio_salida or MODELOS_DIR)
    return modelo, ruta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=DATOS_DIR)
    parser.add_argument("--salida", type=Path, default=MODELOS_DIR)
    parser.add_argument("--ocultas", type=int, default=OCULTAS)
    parser.add_argument("--epocas", type=int, default=EPOCAS)
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    parser.add_argument("--lr", type=float, default=0.01)
    args = parser.parse_args(argv)

    if not disponible():
        print("PyTorch no está instalado; no se pudo entrenar recomendaciones.")
        return 1

    dataset = cargar_o_construir_dataset(args.datos)
    modelo, ruta = entrenar_desde_dataset(
        dataset,
        directorio_salida=args.salida,
        ocultas=args.ocultas,
        epocas=args.epocas,
        semilla=args.semilla,
        tasa_aprendizaje=args.lr,
    )
    if modelo is None or ruta is None:
        print("No hubo datos suficientes para entrenar el autoencoder.")
        return 1

    print(
        f"Autoencoder entrenado: {modelo['clientes']} clientes, "
        f"{len(modelo['productos'])} productos -> {ruta}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
