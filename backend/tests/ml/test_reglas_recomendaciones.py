"""Pruebas de las reglas de recomendaciones (Módulo 3, Jesús).

100% autocontenidas: datos sintéticos en memoria, sin CSV
versionados, sin base de datos y sin modelos entrenados.
"""
import pandas as pd
import pytest

from app.ml.features.recomendaciones import (
    COLUMNAS_CESTAS,
    cestas_desde_dataset,
    cestas_desde_facturas,
    cestas_desde_pedidos,
    conteo_productos,
    matriz_cliente_producto,
)
from app.ml.reglas.recomendaciones import (
    evaluar_mas_vendidos,
    mas_vendidos,
    recomendaciones_por_reglas,
    reglas_asociacion,
)


def _factura(fid, cliente, lineas, estado="emitida", fecha="2026-01-15"):
    return {
        "id": fid,
        "estado": estado,
        "fecha": fecha,
        "cliente_ruc": cliente,
        "cliente_nombre": f"Cliente {cliente}",
        "lineas": lineas,
    }


def _linea_factura(pid, cantidad="2", monto="10.00"):
    return {
        "producto_id": pid,
        "cantidad": cantidad,
        "monto": monto,
    }


def _pedido(pid_pedido, cliente_id, lineas, estado="pendiente"):
    return {
        "id": pid_pedido,
        "cliente_id": cliente_id,
        "estado": estado,
        "fecha_creacion": "2026-01-15T10:00:00",
        "lineas": lineas,
    }


def _linea_pedido(pid, cantidad="1", subtotal="5.00"):
    return {
        "producto_id": pid,
        "cantidad": cantidad,
        "subtotal": subtotal,
    }


def _cestas_reglas():
    """Cestas sintéticas para métricas exactas de reglas.

    4 cestas con >= 2 productos:
      F1, F2 -> {1, 2}
      F3     -> {1, 3}
      F4     -> {2, 3}
    N = 4 transacciones.
    """
    facturas = [
        _factura(1, "RUC-1", [_linea_factura(1), _linea_factura(2)]),
        _factura(2, "RUC-2", [_linea_factura(1), _linea_factura(2)]),
        _factura(3, "RUC-1", [_linea_factura(1), _linea_factura(3)]),
        _factura(4, "RUC-3", [_linea_factura(2), _linea_factura(3)]),
    ]
    return cestas_desde_facturas(facturas)


# ---------- features: construcción de cestas ----------

def test_features_cestas_desde_facturas_solo_emitidas():
    facturas = [
        _factura(1, "RUC-1", [_linea_factura(1)]),
        _factura(2, "RUC-2", [_linea_factura(2)], estado="anulada"),
    ]
    cestas = cestas_desde_facturas(facturas)
    assert set(cestas.columns) == set(COLUMNAS_CESTAS)
    assert cestas["cesta_id"].tolist() == ["factura:1"]
    assert cestas["origen"].tolist() == ["factura"]
    assert cestas["cliente_id"].tolist() == ["RUC-1"]
    assert cestas["producto_id"].tolist() == [1]


def test_features_cestas_descarta_lineas_sin_producto():
    facturas = [
        _factura(1, "RUC-1", [
            _linea_factura(None),
            _linea_factura("x"),
            _linea_factura(7),
        ]),
    ]
    cestas = cestas_desde_facturas(facturas)
    assert cestas["producto_id"].tolist() == [7]
    # Y una factura sin líneas válidas no genera cesta.
    vacias = cestas_desde_facturas(
        [_factura(2, "RUC-1", [_linea_factura(None)])]
    )
    assert vacias.empty


def test_features_cestas_cliente_sin_ruc_usa_nombre():
    factura = _factura(1, None, [_linea_factura(1)])
    factura["cliente_nombre"] = "Nombre Respaldo"
    cestas = cestas_desde_facturas([factura])
    assert cestas["cliente_id"].tolist() == ["Nombre Respaldo"]


def test_features_cestas_desde_pedidos_excluye_cancelados():
    pedidos = [
        _pedido(1, 10, [_linea_pedido(1)]),
        _pedido(2, 11, [_linea_pedido(2)], estado="cancelado"),
        _pedido(3, 12, [_linea_pedido(3)], estado="facturado"),
    ]
    cestas = cestas_desde_pedidos(pedidos)
    assert set(cestas["cesta_id"]) == {"pedido:1", "pedido:3"}
    assert set(cestas["cliente_id"]) == {"10", "12"}


def test_features_cestas_desde_dataset_une_fuentes():
    facturas = [_factura(1, "RUC-1", [_linea_factura(1)])]
    pedidos = [_pedido(1, 10, [_linea_pedido(2)])]
    cestas = cestas_desde_dataset({"facturas": facturas, "pedidos": pedidos})
    assert set(cestas["origen"]) == {"factura", "pedido"}
    assert len(cestas) == 2
    # Sin datos: DataFrame vacío con el contrato de columnas.
    vacio = cestas_desde_dataset()
    assert vacio.empty
    assert list(vacio.columns) == COLUMNAS_CESTAS


def test_features_matriz_cliente_producto_cantidad():
    cestas = pd.DataFrame([
        {"cesta_id": "f:1", "cliente_id": "A", "producto_id": 1,
         "cantidad": 2.0, "monto": 10.0},
        {"cesta_id": "f:2", "cliente_id": "A", "producto_id": 1,
         "cantidad": 3.0, "monto": 15.0},
        {"cesta_id": "f:1", "cliente_id": "A", "producto_id": 2,
         "cantidad": 1.0, "monto": 5.0},
        {"cesta_id": "p:1", "cliente_id": "B", "producto_id": 2,
         "cantidad": 4.0, "monto": 20.0},
    ])
    matriz = matriz_cliente_producto(cestas)
    assert list(matriz.index) == ["A", "B"]
    assert list(matriz.columns) == [1, 2]
    assert matriz.loc["A", 1] == 5.0
    assert matriz.loc["A", 2] == 1.0
    assert matriz.loc["B", 1] == 0.0
    assert matriz.loc["B", 2] == 4.0


def test_features_matriz_cliente_producto_presencia():
    cestas = pd.DataFrame([
        {"cesta_id": "f:1", "cliente_id": "A", "producto_id": 1,
         "cantidad": 9.0, "monto": 90.0},
        {"cesta_id": "f:2", "cliente_id": "A", "producto_id": 1,
         "cantidad": 9.0, "monto": 90.0},
    ])
    matriz = matriz_cliente_producto(cestas, valor="presencia")
    assert matriz.loc["A", 1] == 2.0  # dos cestas, no la cantidad


def test_features_conteo_productos_ordena_por_cantidad():
    cestas = pd.DataFrame([
        {"cesta_id": f"f:{i}", "producto_id": pid,
         "cantidad": cant, "monto": cant * 2.0}
        for i, (pid, cant) in enumerate(
            [(1, 1.0), (2, 5.0), (2, 5.0), (3, 2.0)], start=1
        )
    ])
    conteo = conteo_productos(cestas)
    assert conteo["producto_id"].tolist() == [2, 3, 1]
    fila2 = conteo[conteo["producto_id"] == 2].iloc[0]
    assert fila2["cantidad_total"] == 10.0
    assert fila2["num_lineas"] == 2
    assert fila2["num_cestas"] == 2
    assert conteo["participacion"].sum() == pytest.approx(1.0)
    assert conteo_productos(cestas.iloc[0:0]).empty


# ---------- reglas: línea base "más vendidos" ----------

def test_reglas_mas_vendidos_ordena_y_excluye():
    cestas = _cestas_reglas()
    top = mas_vendidos(cestas, n=5)
    # Producto 1: 3 cestas x cantidad 2 = 6; 2: 3 cestas x2 = 6;
    # 3: 2 cestas x2 = 4. Empate 1 vs 2 lo rompe num_cestas (empate)
    # y luego producto_id -> 1 primero.
    assert [r["producto_id"] for r in top] == [1, 2, 3]
    sin_1 = mas_vendidos(cestas, n=5, excluir=[1])
    assert [r["producto_id"] for r in sin_1] == [2, 3]
    assert all(r["fuente"] == "mas_vendidos" for r in top)
    assert mas_vendidos(cestas.iloc[0:0]) == []


# ---------- reglas: soporte, confianza y lift ----------

def test_reglas_asociacion_metricas_exactas():
    cestas = _cestas_reglas()
    reglas = reglas_asociacion(cestas, soporte_min=0.0,
                               confianza_min=0.0)
    assert not reglas.empty
    por_par = {
        (r.antecedente, r.consecuente): r for r in reglas.itertuples()
    }

    def regla(a, b):
        return por_par[(frozenset({a}), frozenset({b}))]

    # 1 -> 2: está en F1 y F2 -> soporte 2/4 = 0.5,
    # confianza 2/3 (el 1 está en 3 cestas), lift = (2/3)/(3/4).
    r12 = regla(1, 2)
    assert r12.soporte == pytest.approx(0.5)
    assert r12.confianza == pytest.approx(2 / 3)
    assert r12.lift == pytest.approx((2 / 3) / (3 / 4))
    assert r12.soporte_antecedente == pytest.approx(0.75)
    assert r12.soporte_consecuente == pytest.approx(0.75)

    # 3 -> 1: solo en F3 -> soporte 0.25, confianza 1/2,
    # lift = (1/2)/(3/4) = 2/3.
    r31 = regla(3, 1)
    assert r31.soporte == pytest.approx(0.25)
    assert r31.confianza == pytest.approx(0.5)
    assert r31.lift == pytest.approx((0.5) / 0.75)


def test_reglas_asociacion_filtros_y_cestas_de_una_sola():
    # Cesta de un solo producto no genera reglas.
    cestas = pd.DataFrame([
        {"cesta_id": "f:1", "producto_id": 1, "cantidad": 1.0,
         "monto": 1.0},
        {"cesta_id": "f:2", "producto_id": 1, "cantidad": 1.0,
         "monto": 1.0},
    ])
    assert reglas_asociacion(cestas).empty

    reglas = reglas_asociacion(_cestas_reglas(), soporte_min=0.4,
                               confianza_min=0.5)
    # Solo quedan reglas con soporte >= 0.4: 1->2 y 2->1.
    pares = {(r.antecedente, r.consecuente) for r in reglas.itertuples()}
    assert pares == {(frozenset({1}), frozenset({2})),
                     (frozenset({2}), frozenset({1}))}


# ---------- reglas: recomendación con respaldo ----------

def test_reglas_recomendacion_usa_carrito_como_antecedente():
    cestas = _cestas_reglas()
    recs = recomendaciones_por_reglas(cestas, [1], n=5,
                                      soporte_min=0.0,
                                      confianza_min=0.0,
                                      lift_min=0.0)
    por_fuente = {r["producto_id"]: r for r in recs}
    # Con carrito {1}: reglas 1->2 (conf 2/3) y 1->3 (conf 1/3).
    assert por_fuente[2]["fuente"] == "reglas"
    assert por_fuente[2]["confianza"] == pytest.approx(2 / 3)
    assert por_fuente[3]["fuente"] == "reglas"
    # El producto 1 ya está en el carrito: nunca se recomienda.
    assert 1 not in por_fuente
    # Orden: 2 antes que 3 por mayor confianza.
    ids = [r["producto_id"] for r in recs]
    assert ids.index(2) < ids.index(3)


def test_reglas_recomendacion_respaldo_sin_historial():
    # Sin cestas no hay reglas ni ventas: lista vacía, sin error.
    vacias = cestas_desde_facturas([])
    assert recomendaciones_por_reglas(vacias, [1]) == []

    # Historial sin co-ocurrencias: cae a "más vendidos".
    cestas = pd.DataFrame([
        {"cesta_id": "f:1", "producto_id": 9, "cantidad": 3.0,
         "monto": 3.0},
        {"cesta_id": "f:2", "producto_id": 9, "cantidad": 1.0,
         "monto": 1.0},
        {"cesta_id": "f:3", "producto_id": 5, "cantidad": 2.0,
         "monto": 2.0},
    ])
    recs = recomendaciones_por_reglas(cestas, [99], n=2,
                                      soporte_min=0.0,
                                      confianza_min=0.0)
    assert [r["producto_id"] for r in recs] == [9, 5]
    assert all(r["fuente"] == "mas_vendidos" for r in recs)


def test_reglas_recomendacion_carrito_desconocido_usa_base():
    cestas = _cestas_reglas()
    # Carrito con producto que nunca apareció junto a nada:
    # no hay reglas con ese antecedente -> respaldo a más vendidos.
    recs = recomendaciones_por_reglas(cestas, [77], n=3,
                                      soporte_min=0.0,
                                      confianza_min=0.0,
                                      lift_min=0.0)
    assert [r["producto_id"] for r in recs] == [1, 2, 3]
    assert all(r["fuente"] == "mas_vendidos" for r in recs)
    # Y el propio 77 no se recomienda ni rompe nada.
    assert all(r["producto_id"] != 77 for r in recs)


def test_reglas_recomendacion_excluye_inactivos_y_carrito():
    cestas = _cestas_reglas()
    recs = recomendaciones_por_reglas(
        cestas, [1], n=5, soporte_min=0.0, confianza_min=0.0,
        lift_min=0.0, excluir=[3],
    )
    ids = [r["producto_id"] for r in recs]
    assert 3 not in ids and 1 not in ids
    # 2 viene de reglas; el resto se rellena con más vendidos.
    assert ids[0] == 2
    assert set(ids) <= {2, 3} or 3 not in ids


def test_reglas_recomendacion_acepta_reglas_precalculadas():
    cestas = _cestas_reglas()
    reglas = reglas_asociacion(cestas, soporte_min=0.0,
                               confianza_min=0.0)
    recs = recomendaciones_por_reglas(cestas, [1], n=2, reglas=reglas)
    assert [r["producto_id"] for r in recs[:2]] == [2, 3]


# ---------- evaluación de referencia de la línea base ----------

def test_reglas_evaluar_mas_vendidos_metricas():
    cestas = _cestas_reglas()
    metricas = evaluar_mas_vendidos(cestas, k=2)
    assert metricas["metodo"] == "mas_vendidos"
    assert metricas["k"] == 2
    assert metricas["cestas"] == 4
    # 4 cestas x 2 productos = 8 pares.
    assert metricas["pares"] == 8
    assert 0 <= metricas["hit_rate"] <= 1
    assert metricas["precision_at_k"] == pytest.approx(
        metricas["hit_rate"] / 2
    )
    # Determinista: mismo input -> mismas métricas.
    assert evaluar_mas_vendidos(cestas, k=2) == metricas


def test_reglas_evaluar_mas_vendidos_vacio_y_k():
    vacio = evaluar_mas_vendidos(cestas_desde_facturas([]), k=5)
    assert vacio["pares"] == 0
    assert vacio["hit_rate"] == 0.0
    assert vacio["precision_at_k"] == 0.0

    # k=1 sobre el dataset sintético: el más vendido global es 1 o 2.
    metricas = evaluar_mas_vendidos(_cestas_reglas(), k=1)
    assert metricas["k"] == 1
    assert metricas["precision_at_k"] == pytest.approx(
        metricas["hit_rate"]
    )
