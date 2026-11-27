"""Entrenamiento del autoencoder de recomendaciones (Módulo 3).

Pipeline: CSV de ejemplo -> cestas -> matriz cliente-producto ->
autoencoder -> evaluación leave-one-out contra "más vendidos".
El artefacto final va en `backend/ml_models/` (fuera de Git) y la
app funciona igual sin él.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.datasets import generar_datos as gd  # noqa: E402
from app.ml.evaluacion.recomendaciones import comparar, preparar_casos  # noqa: E402
from app.ml.features.recomendaciones import (  # noqa: E402
    cestas_desde_dataset,
    matriz_cliente_producto,
)
from app.ml.modelos import recomendaciones as modelo  # noqa: E402
from app.ml.reglas.recomendaciones import mas_vendidos  # noqa: E402


def _leer_pedidos(directorio):
    """Pedidos con líneas anidadas desde los CSV de ejemplo."""
    base = Path(directorio)
    lineas_por_pedido = defaultdict(list)
    ruta_lineas = base / "lineas_pedido_ejemplo.csv"
    if ruta_lineas.is_file():
        with ruta_lineas.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                lineas_por_pedido[fila["pedido_id"]].append(fila)

    pedidos = []
    ruta_pedidos = base / "pedidos_ejemplo.csv"
    if not ruta_pedidos.is_file():
        return pedidos
    with ruta_pedidos.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            pedido = dict(fila)
            pedido["lineas"] = sorted(
                lineas_por_pedido.get(fila["id"], []),
                key=lambda linea: int(linea.get("orden") or 0),
            )
            pedidos.append(pedido)
    return pedidos


def cargar_cestas(directorio=gd.SALIDA):
    """Une facturas y pedidos de los CSV en cestas normalizadas."""
    datos = gd.cargar_dataset_ml(directorio)
    pedidos = _leer_pedidos(directorio)
    return cestas_desde_dataset(
        {"facturas": datos.get("facturas"), "pedidos": pedidos}
    )


def casos_desde_cestas(cestas, semilla=20261126):
    """Casos leave-one-out para `evaluacion.preparar_casos`."""
    if cestas is None or getattr(cestas, "empty", True):
        return {}
    por_cesta = defaultdict(set)
    for cesta_id, producto_id in cestas[["cesta_id", "producto_id"]].itertuples(
        index=False, name=None
    ):
        por_cesta[str(cesta_id)].add(int(producto_id))
    return dict(por_cesta)


def _recomendador_linea_base(cestas):
    def recomendar(carrito, k):
        return [
            item["producto_id"]
            for item in mas_vendidos(cestas, n=int(k), excluir=carrito)
        ]

    return recomendar


def _recomendador_modelo(artefacto):
    if artefacto is None:
        return None

    def recomendar(carrito, k):
        items = modelo.recomendar(artefacto, carrito, n=int(k))
        return [item["producto_id"] for item in items] if items else []

    return recomendar


def entrenar(
    directorio=gd.SALIDA,
    *,
    ocultas=modelo.OCULTAS,
    epocas=modelo.EPOCAS,
    semilla=modelo.SEMILLA,
    k=5,
    directorio_modelos=None,
):
    """Entrena y devuelve métricas, artefacto y ruta (si se guardó)."""
    cestas = cargar_cestas(directorio)
    matriz = matriz_cliente_producto(cestas, valor="presencia")
    artefacto = modelo.entrenar_autoencoder(
        matriz, ocultas=ocultas, epocas=epocas, semilla=semilla
    )

    pedidos = casos_desde_cestas(cestas, semilla=semilla)
    casos = preparar_casos(pedidos, semilla=semilla)
    metricas = comparar(
        _recomendador_modelo(artefacto),
        _recomendador_linea_base(cestas),
        casos,
        k=k,
    )

    ruta = None
    if directorio_modelos is not None and artefacto is not None:
        ruta = modelo.guardar_modelo(artefacto, directorio_modelos)

    return {
        "clientes": int(matriz.shape[0]) if not matriz.empty else 0,
        "productos": int(matriz.shape[1]) if not matriz.empty else 0,
        "cestas": len(casos),
        "modelo": modelo.NOMBRE_MODELO if artefacto else None,
        "metricas": metricas,
        "ruta_modelo": str(ruta) if ruta else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=gd.SALIDA)
    parser.add_argument("--ocultas", type=int, default=modelo.OCULTAS)
    parser.add_argument("--epocas", type=int, default=modelo.EPOCAS)
    parser.add_argument("--semilla", type=int, default=modelo.SEMILLA)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--sin-guardar", action="store_true")
    args = parser.parse_args(argv)

    resultado = entrenar(
        directorio=args.datos,
        ocultas=args.ocultas,
        epocas=args.epocas,
        semilla=args.semilla,
        k=args.k,
        directorio_modelos=None if args.sin_guardar else modelo.MODELOS_DIR,
    )
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
