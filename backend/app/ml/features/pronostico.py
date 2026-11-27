"""Rasgos para pronosticar facturación: agregación mensual.

Solo biblioteca estándar para que el módulo se pueda importar en
cualquier entorno (la API no necesita pandas para cargarlo).

Niveles soportados:
- "total": suma de Factura.total por mes (solo estado 'emitida').
- "producto": suma de LineaFactura.monto por mes y producto_id.
- "categoria": suma de LineaFactura.monto por mes y categoria.
"""
from __future__ import annotations


def _mes(fecha) -> str:
    return str(fecha)[:7]  # 'YYYY-MM'


def _total_factura(factura) -> float:
    try:
        return float(factura.get("total") or 0)
    except (TypeError, ValueError):
        return 0.0


def _monto_linea(linea) -> float:
    try:
        return float(linea.get("monto") or 0)
    except (TypeError, ValueError):
        return 0.0


def _facturas_validas(facturas, incluir_anuladas):
    return [
        f for f in facturas
        if incluir_anuladas or f.get("estado") != "anulada"
    ]


def ventas_mensuales(facturas, lineas=None, nivel="total",
                     incluir_anuladas=False):
    """Ventas agregadas por mes.

    Devuelve lista de dicts {periodo: 'YYYY-MM', clave, total}, ordenada.
    nivel='total' usa Factura.total; 'producto'/'categoria' usan
    LineaFactura.monto uniendo por factura_id.
    """
    if nivel not in ("total", "producto", "categoria"):
        raise ValueError(f"nivel inválido: {nivel}")

    validas = _facturas_validas(facturas, incluir_anuladas)

    if nivel == "total":
        acum = {}
        for f in validas:
            m = _mes(f.get("fecha"))
            acum[m] = acum.get(m, 0.0) + _total_factura(f)
        return [
            {"periodo": m, "clave": "total", "total": round(v, 2)}
            for m, v in sorted(acum.items())
        ]

    campo = "producto_id" if nivel == "producto" else "categoria"
    idx = {str(f.get("id")): f for f in validas}
    acum = {}
    for linea in lineas or []:
        f = idx.get(str(linea.get("factura_id")))
        if f is None:
            continue
        m = _mes(f.get("fecha"))
        clave = str(linea.get(campo) or "sin_dato")
        llave = (m, clave)
        acum[llave] = acum.get(llave, 0.0) + _monto_linea(linea)
    return [
        {"periodo": m, "clave": c, "total": round(v, 2)}
        for (m, c), v in sorted(acum.items())
    ]


def matriz_mensual(facturas, lineas=None, nivel="total",
                   incluir_anuladas=False):
    """Pivote mes x clave con ceros en meses sin ventas.

    Devuelve {"periodos": [...], "claves": [...], "valores": {clave: [...]}}.
    La posición i de cada lista de valores corresponde a periodos[i].
    """
    registros = ventas_mensuales(
        facturas, lineas=lineas, nivel=nivel,
        incluir_anuladas=incluir_anuladas,
    )
    periodos = sorted({r["periodo"] for r in registros})
    claves = sorted({r["clave"] for r in registros})
    datos = {(r["periodo"], r["clave"]): r["total"] for r in registros}
    valores = {
        c: [round(datos.get((p, c), 0.0), 2) for p in periodos]
        for c in claves
    }
    return {"periodos": periodos, "claves": claves, "valores": valores}
