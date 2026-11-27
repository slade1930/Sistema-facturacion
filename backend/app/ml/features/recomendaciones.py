"""Rasgos para recomendaciones (Módulo 3, dueño: Jesús).

Convierte facturas y pedidos en "cestas" normalizadas y deriva la
matriz cliente-producto y los conteos base que usan las reglas de
asociación y el modelo del autoencoder. Todo funciona en memoria,
sin base de datos, sin `db.commit()` y sin entrenar nada.

Contrato del DataFrame de cestas (lo comparten reglas, modelos y
evaluación):

    cesta_id     identificador único de la transacción (factura o pedido)
    origen       "factura" o "pedido"
    cliente_id   RUC/nombre del cliente en facturas; id en pedidos
    fecha        fecha de la transacción (texto ISO, puede ser None)
    producto_id  id entero del producto (las líneas sin id se descartan)
    cantidad     cantidad numérica de la línea
    monto        monto numérico de la línea
"""
from __future__ import annotations

import pandas as pd

COLUMNAS_CESTAS = [
    "cesta_id",
    "origen",
    "cliente_id",
    "fecha",
    "producto_id",
    "cantidad",
    "monto",
]

# Pedidos cancelados no cuentan como intención de compra real.
ESTADOS_PEDIDO_EXCLUIDOS = {"cancelado"}


def _a_float(valor, defecto=0.0):
    """Decimal/str/None -> float; lo que llega de CSV es texto."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _a_producto_id(valor):
    """producto_id -> int o None si falta o no es numérico."""
    if valor is None:
        return None
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def _cliente_de_factura(factura):
    """Cliente estable para la matriz: RUC, si no nombre, si no 'sin-cliente'."""
    for campo in ("cliente_ruc", "cliente_nombre"):
        valor = factura.get(campo)
        if valor:
            return str(valor)
    return "sin-cliente"


def _cesta_vacia():
    return pd.DataFrame(columns=COLUMNAS_CESTAS)


def cestas_desde_facturas(facturas, solo_emitidas=True):
    """Cestas desde facturas con líneas anidadas (dicts del generador/CSV).

    Cada factura aporta una cesta con sus líneas. Por defecto solo se
    usan facturas 'emitida' (las anuladas no son demanda real). Las
    líneas sin `producto_id` válido se descartan.
    """
    filas = []
    for factura in facturas or []:
        if solo_emitidas and factura.get("estado") != "emitida":
            continue
        cesta_id = factura.get("id")
        if cesta_id is None:
            continue
        cliente_id = _cliente_de_factura(factura)
        fecha = factura.get("fecha")
        for linea in factura.get("lineas") or []:
            producto_id = _a_producto_id(linea.get("producto_id"))
            if producto_id is None:
                continue
            filas.append({
                "cesta_id": f"factura:{cesta_id}",
                "origen": "factura",
                "cliente_id": cliente_id,
                "fecha": fecha,
                "producto_id": producto_id,
                "cantidad": _a_float(linea.get("cantidad"), 1.0),
                "monto": _a_float(linea.get("monto")),
            })
    if not filas:
        return _cesta_vacia()
    return pd.DataFrame(filas, columns=COLUMNAS_CESTAS)


def cestas_desde_pedidos(pedidos, estados_excluidos=None):
    """Cestas desde pedidos B2B con líneas anidadas.

    Por defecto se excluyen los pedidos 'cancelado'; el resto
    (pendiente, procesando, facturado) cuenta como demanda. La
    `cantidad` viene en unidades del empaque elegido, tal cual está.
    """
    excluidos = set(
        ESTADOS_PEDIDO_EXCLUIDOS
        if estados_excluidos is None
        else estados_excluidos
    )
    filas = []
    for pedido in pedidos or []:
        if str(pedido.get("estado", "")).lower() in excluidos:
            continue
        cesta_id = pedido.get("id")
        if cesta_id is None:
            continue
        for linea in pedido.get("lineas") or []:
            producto_id = _a_producto_id(linea.get("producto_id"))
            if producto_id is None:
                continue
            filas.append({
                "cesta_id": f"pedido:{cesta_id}",
                "origen": "pedido",
                "cliente_id": str(pedido.get("cliente_id") or "sin-cliente"),
                "fecha": pedido.get("fecha_creacion"),
                "producto_id": producto_id,
                "cantidad": _a_float(linea.get("cantidad"), 1.0),
                "monto": _a_float(linea.get("subtotal")),
            })
    if not filas:
        return _cesta_vacia()
    return pd.DataFrame(filas, columns=COLUMNAS_CESTAS)


def cestas_desde_dataset(facturas=None, pedidos=None):
    """Une cestas de facturas y pedidos en un solo DataFrame.

    Acepta los dicts de `construir_dataset` (claves 'facturas' y
    'pedidos') o los pasa por separado. Sin argumentos devuelve el
    DataFrame vacío con el contrato de columnas.
    """
    if isinstance(facturas, dict):
        dataset = facturas
        pedidos = pedidos if pedidos is not None else dataset.get("pedidos")
        facturas = dataset.get("facturas")
    partes = []
    cestas_f = cestas_desde_facturas(facturas)
    if not cestas_f.empty:
        partes.append(cestas_f)
    cestas_p = cestas_desde_pedidos(pedidos)
    if not cestas_p.empty:
        partes.append(cestas_p)
    if not partes:
        return _cesta_vacia()
    return pd.concat(partes, ignore_index=True)[COLUMNAS_CESTAS]


def matriz_cliente_producto(cestas, valor="cantidad"):
    """Matriz cliente x producto para el autoencoder.

    `valor` elige qué suma cada celda:
      - "cantidad": unidades vendidas (default).
      - "monto":   dinero facturado.
      - "presencia": 1 por cada cesta que contiene el producto
        (ignora la cantidad y sirve para reglas binarias).

    Devuelve un DataFrame con índice `cliente_id`, columnas
    `producto_id` y 0 donde no hubo compra. Cestas vacías -> matriz
    vacía.
    """
    if cestas is None or cestas.empty:
        return pd.DataFrame()
    if valor == "presencia":
        base = cestas[["cliente_id", "producto_id", "cesta_id"]].drop_duplicates(
            subset=["cliente_id", "producto_id", "cesta_id"]
        )
        agregada = base.assign(_valor=1.0)
        columna = "_valor"
    elif valor == "monto":
        agregada = cestas[["cliente_id", "producto_id", "monto"]]
        columna = "monto"
    else:  # "cantidad" por defecto; cualquier otro valor cae acá
        agregada = cestas[["cliente_id", "producto_id", "cantidad"]]
        columna = "cantidad"
    matriz = agregada.pivot_table(
        index="cliente_id",
        columns="producto_id",
        values=columna,
        aggfunc="sum",
        fill_value=0.0,
    )
    return matriz.sort_index(axis=1)


def conteo_productos(cestas):
    """Conteos base por producto, ordenados de más a menos vendido.

    Columnas: producto_id (índice), cantidad_total, monto_total,
    num_cestas, num_lineas y participacion (fracción de la cantidad
    total). Es la entrada natural de la línea base "más vendidos".
    """
    columnas = [
        "producto_id", "cantidad_total", "monto_total",
        "num_cestas", "num_lineas", "participacion",
    ]
    if cestas is None or cestas.empty:
        return pd.DataFrame(columns=columnas)
    grupo = cestas.groupby("producto_id")
    conteo = pd.DataFrame({
        "cantidad_total": grupo["cantidad"].sum(),
        "monto_total": grupo["monto"].sum(),
        "num_cestas": grupo["cesta_id"].nunique(),
        "num_lineas": grupo.size(),
    })
    total = conteo["cantidad_total"].sum()
    conteo["participacion"] = (
        conteo["cantidad_total"] / total if total else 0.0
    )
    conteo = conteo.reset_index().sort_values(
        ["cantidad_total", "num_cestas", "producto_id"],
        ascending=[False, False, True],
    )
    return conteo[columnas].reset_index(drop=True)
