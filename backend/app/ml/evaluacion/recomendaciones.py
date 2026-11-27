# app/ml/evaluacion/recomendaciones.py
import random
from collections.abc import Callable, Sequence

# (productos_del_carrito, k) -> ids de producto ordenados de mejor a peor
Recomendador = Callable[[Sequence[int], int], list[int]]


def preparar_casos(
    pedidos: dict[int, Sequence[int]], semilla: int = 42
) -> list[tuple[list[int], int]]:
    """Esconde un producto por pedido. Devuelve (visibles, oculto).

    Se ignoran los pedidos con menos de 2 productos distintos.
    La semilla fija hace que el resultado sea repetible.
    """
    rng = random.Random(semilla)
    casos = []
    for pedido_id in sorted(pedidos):
        productos = sorted(set(pedidos[pedido_id]))
        if len(productos) < 2:
            continue
        oculto = rng.choice(productos)
        casos.append(([p for p in productos if p != oculto], oculto))
    return casos


def evaluar(recomendador: Recomendador, casos, k: int = 5) -> dict:
    if not casos:
        return {"casos": 0, "k": k, "hit_rate": None, "precision_at_k": None}
    aciertos = 0
    for visibles, oculto in casos:
        top = [p for p in recomendador(visibles, k) if p not in visibles][:k]
        if oculto in top:
            aciertos += 1
    hit_rate = aciertos / len(casos)
    # Con un solo producto escondido, precision@k = hit_rate / k
    return {"casos": len(casos), "k": k, "hit_rate": hit_rate, "precision_at_k": hit_rate / k}


def comparar(modelo: Recomendador | None, linea_base: Recomendador, casos, k: int = 5) -> dict:
    """Si no hay modelo entrenado, el resultado es 'sin evaluar' (regla del ML)."""
    resultado = {"linea_base": evaluar(linea_base, casos, k)}
    resultado["modelo"] = evaluar(modelo, casos, k) if modelo else "sin evaluar"
    return resultado