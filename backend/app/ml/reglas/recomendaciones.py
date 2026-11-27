"""Reglas base de recomendaciones (Módulo 3, dueño: Jesús).

Línea base "más vendidos" y reglas de asociación con soporte,
confianza y lift calculadas en pandas puro (sin mlxtend ni otra
dependencia). Nada de esto entrena un modelo: funciona siempre,
aunque no haya datos o el modelo del autoencoder no exista.

El ML sugiere, nunca bloquea: carritos vacíos, productos
desconocidos o falta de historial devuelven la línea base o una
lista vacía, jamás una excepción.
"""
from __future__ import annotations

import pandas as pd

from app.ml.features.recomendaciones import conteo_productos

COLUMNAS_REGLAS = [
    "antecedente", "consecuente", "soporte", "confianza",
    "soporte_antecedente", "soporte_consecuente", "lift",
]


def _items_por_cesta(cestas):
    """{cesta_id: set(producto_id)} solo con ids válidos."""
    if cestas is None or cestas.empty:
        return {}
    items = (
        cestas[["cesta_id", "producto_id"]]
        .dropna()
        .drop_duplicates()
    )
    return {
        cesta_id: set(grupo["producto_id"])
        for cesta_id, grupo in items.groupby("cesta_id")
    }


def _excluir_set(excluir):
    return {int(p) for p in (excluir or [])}


def mas_vendidos(cestas, n=5, excluir=None, conteo=None):
    """Línea base: productos más vendidos (sin entrenar nada).

    Ranking por cantidad total vendida, desempate por número de
    cestas y luego por id. `excluir` saca productos ya en el
    carrito o inactivos (ids). Devuelve una lista de dicts:

        {"producto_id": int, "puntaje": float, "fuente": "mas_vendidos"}

    `puntaje` es la cantidad total vendida. Sin datos devuelve [].
    """
    if conteo is None:
        conteo = conteo_productos(cestas)
    excluidos = _excluir_set(excluir)
    resultados = []
    if conteo is None or conteo.empty:
        return resultados
    for fila in conteo.itertuples(index=False):
        producto_id = int(fila.producto_id)
        if producto_id in excluidos:
            continue
        resultados.append({
            "producto_id": producto_id,
            "puntaje": float(fila.cantidad_total),
            "fuente": "mas_vendidos",
        })
        if len(resultados) >= n:
            break
    return resultados


def reglas_asociacion(cestas, soporte_min=0.01, confianza_min=0.05,
                      lift_min=0.0, max_reglas=None):
    """Reglas A -> B con soporte, confianza y lift en pandas puro.

    Una "transacción" es una cesta con al menos 2 productos
    distintos; el soporte se calcula sobre esas cestas (N). Solo se
    generan reglas de un ítem antecedente a un ítem consecuente
    (la base para extender a conjuntos más grandes).

    Devuelve un DataFrame con columnas:
      antecedente, consecuente  -> frozenset({producto_id})
      soporte    P(A ∪ B) = cestas con A y B / N
      confianza  P(B | A) = cestas con A y B / cestas con A
      lift       confianza / P(B), con P(B) = cestas con B / N
      soporte_antecedente, soporte_consecuente  (P(A) y P(B))

    Filtros: soporte >= soporte_min, confianza >= confianza_min y
    lift >= lift_min. Orden: confianza desc, lift desc, soporte desc.
    """
    vacio = pd.DataFrame(columns=COLUMNAS_REGLAS)
    por_cesta = _items_por_cesta(cestas)
    cestas_validas = {
        cid for cid, items in por_cesta.items() if len(items) >= 2
    }
    if not cestas_validas:
        return vacio

    items = (
        cestas.loc[
            cestas["cesta_id"].isin(cestas_validas),
            ["cesta_id", "producto_id"],
        ]
        .dropna()
        .drop_duplicates()
    )
    n_transacciones = items["cesta_id"].nunique()
    if n_transacciones == 0:
        return vacio

    # Pares ordenados (a, b) con a != b dentro de la misma cesta.
    pares = items.merge(
        items, on="cesta_id", suffixes=("_a", "_b")
    )
    pares = pares[pares["producto_id_a"] != pares["producto_id_b"]]
    if pares.empty:
        return vacio

    conteo_ab = (
        pares.groupby(["producto_id_a", "producto_id_b"])
        .size()
        .rename("n_ab")
        .reset_index()
    )
    conteo_item = (
        items.groupby("producto_id")["cesta_id"]
        .nunique()
        .rename("n_item")
        .reset_index()
    )

    reglas = conteo_ab.merge(
        conteo_item.rename(columns={"producto_id": "producto_id_a",
                                    "n_item": "n_a"}),
        on="producto_id_a",
    ).merge(
        conteo_item.rename(columns={"producto_id": "producto_id_b",
                                    "n_item": "n_b"}),
        on="producto_id_b",
    )
    reglas["soporte"] = reglas["n_ab"] / n_transacciones
    reglas["soporte_antecedente"] = reglas["n_a"] / n_transacciones
    reglas["soporte_consecuente"] = reglas["n_b"] / n_transacciones
    reglas["confianza"] = reglas["n_ab"] / reglas["n_a"]
    reglas["lift"] = reglas["confianza"] / reglas["soporte_consecuente"]
    reglas["antecedente"] = reglas["producto_id_a"].map(
        lambda p: frozenset({int(p)})
    )
    reglas["consecuente"] = reglas["producto_id_b"].map(
        lambda p: frozenset({int(p)})
    )

    reglas = reglas[
        (reglas["soporte"] >= soporte_min)
        & (reglas["confianza"] >= confianza_min)
        & (reglas["lift"] >= lift_min)
    ]
    reglas = reglas.sort_values(
        ["confianza", "lift", "soporte", "producto_id_a", "producto_id_b"],
        ascending=[False, False, False, True, True],
    )
    if max_reglas is not None:
        reglas = reglas.head(max_reglas)
    return reglas[COLUMNAS_REGLAS].reset_index(drop=True)


def recomendaciones_por_reglas(cestas, productos_en_cesta, n=5,
                               soporte_min=0.01, confianza_min=0.05,
                               lift_min=1.0, reglas=None, excluir=None,
                               topup_mas_vendidos=True):
    """Recomienda con reglas de asociación y respaldo a "más vendidos".

    `productos_en_cesta` son los productos que el cliente ya tiene
    (el carrito actual). Solo aplican reglas cuyo antecedente está
    contenido en esa cesta; nunca se recomienda lo que ya está ni lo
    que esté en `excluir` (inactivos, por ejemplo).

    El puntaje de cada candidato es la suma de las confianzas de
    las reglas que lo respaldan; se guarda la confianza/lift/soporte
    de la mejor regla. Si no hay reglas suficientes (o no hay
    historial), se rellena hasta `n` con "más vendidos". Cada ítem
    devuelto es::

        {"producto_id": int, "puntaje": float, "fuente": str,
         "confianza": float|None, "lift": float|None,
         "soporte": float|None}

    Funciona sin entrenar: sin cestas o sin reglas devuelve la línea
    base o [] si tampoco hay ventas.
    """
    base = _excluir_set(productos_en_cesta)
    excluidos = base | _excluir_set(excluir)
    if reglas is None:
        reglas = reglas_asociacion(
            cestas, soporte_min=soporte_min,
            confianza_min=confianza_min, lift_min=lift_min,
        )

    puntajes = {}
    mejores = {}
    if reglas is not None and not reglas.empty:
        for fila in reglas.itertuples(index=False):
            if not fila.antecedente <= base:
                continue
            for producto_id in fila.consecuente:
                pid = int(producto_id)
                if pid in excluidos:
                    continue
                puntajes[pid] = puntajes.get(pid, 0.0) + float(
                    fila.confianza
                )
                actual = mejores.get(pid)
                if actual is None or fila.confianza > actual[0]:
                    mejores[pid] = (
                        float(fila.confianza),
                        float(fila.lift),
                        float(fila.soporte),
                    )

    resultados = []
    for pid in sorted(puntajes, key=lambda p: (-puntajes[p], p)):
        confianza, lift, soporte = mejores[pid]
        resultados.append({
            "producto_id": pid,
            "puntaje": puntajes[pid],
            "fuente": "reglas",
            "confianza": confianza,
            "lift": lift,
            "soporte": soporte,
        })

    if topup_mas_vendidos and len(resultados) < n:
        ya = {r["producto_id"] for r in resultados}
        for item in mas_vendidos(
            cestas, n=n + len(ya) + len(excluidos), excluir=excluidos
        ):
            if item["producto_id"] in ya:
                continue
            resultados.append({
                "producto_id": item["producto_id"],
                "puntaje": item["puntaje"],
                "fuente": "mas_vendidos",
                "confianza": None,
                "lift": None,
                "soporte": None,
            })
            if len(resultados) >= n:
                break
    return resultados[:n]


def evaluar_mas_vendidos(cestas, k=5):
    """Línea base de referencia: hit rate y precision@k de "más vendidos".

    Esquema leave-one-out por cesta: para cada producto de cada
    cesta se "esconde" (sale del carrito) y se recomiendan los top-k
    por cantidad vendida en las demás cestas, excluyendo lo que
    queda en el carrito. Hit = el producto escondido aparece en el
    top-k. Sirve de referencia para comparar reglas y el modelo en
    `app.ml.evaluacion` (dueño: mdeh25-droid).

    Devuelve::

        {"metodo": "mas_vendidos", "k": int, "cestas": int,
         "pares": int, "hits": int,
         "hit_rate": float, "precision_at_k": float}

    Sin datos devuelve métricas en 0.0 (nunca lanza excepción).
    """
    vacio = {
        "metodo": "mas_vendidos", "k": k, "cestas": 0,
        "pares": 0, "hits": 0, "hit_rate": 0.0,
        "precision_at_k": 0.0,
    }
    por_cesta = _items_por_cesta(cestas)
    por_cesta = {cid: items for cid, items in por_cesta.items()
                 if items}
    if not por_cesta:
        return vacio

    items = (
        cestas.loc[cestas["cesta_id"].isin(por_cesta),
                  ["cesta_id", "producto_id"]]
        .dropna()
        .drop_duplicates()
    )
    conteo_global = items.groupby("producto_id").size().to_dict()

    pares = 0
    hits = 0
    for cesta_id, productos in por_cesta.items():
        # Conteos sin esta cesta (leave-one-out a nivel cesta).
        conteo = dict(conteo_global)
        for pid in productos:
            conteo[pid] = conteo.get(pid, 0) - 1
            if conteo[pid] <= 0:
                conteo.pop(pid, None)
        ranking = sorted(
            conteo, key=lambda p: (-conteo[p], p)
        )
        for escondido in productos:
            restantes = productos - {escondido}
            top_k = []
            for pid in ranking:
                if pid in restantes:
                    continue
                top_k.append(pid)
                if len(top_k) >= k:
                    break
            pares += 1
            if escondido in top_k:
                hits += 1

    return {
        "metodo": "mas_vendidos",
        "k": k,
        "cestas": len(por_cesta),
        "pares": pares,
        "hits": hits,
        "hit_rate": hits / pares if pares else 0.0,
        "precision_at_k": (hits / k) / pares if pares else 0.0,
    }
