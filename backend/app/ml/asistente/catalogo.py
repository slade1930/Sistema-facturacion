"""Catálogo de consultas del asistente (paso 0; se arma en el paso 4).

Módulo app.ml.asistente. Dueño: Fernando (Módulo 4). Depende de los repositorios existentes.
Seis consultas predefinidas, nunca SQL generado.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal
from enum import Enum

from app.models.facturacion import EstadoFactura
from app.repositories.facturacion import FacturaRepository

LIMITE = 10_000
CENTAVOS = Decimal("0.01")

ESTADOS_FACTURABLES = frozenset(
    estado.value for estado in (EstadoFactura.EMITIDA, EstadoFactura.EN_REVISION)
)

INTENCIONES = (
    "ventas_por_mes",
    "ventas_por_cliente",
    "ventas_por_producto",
    "facturas_anuladas",
    "top_productos",
    "facturas_en_revision",
)

CONSULTAS_PREDEFINIDAS = {
    "ventas_por_mes": "¿cuánto facturamos por mes?",
    "ventas_por_cliente": "¿cuánto facturamos por cliente?",
    "ventas_por_producto": "¿cuánto facturamos por producto?",
    "facturas_anuladas": "¿cuántas facturas están anuladas?",
    "top_productos": "¿cuáles son los productos más vendidos?",
    "facturas_en_revision": "¿cuántas facturas están en revisión?",
}


def _valor_estado(estado) -> str:
    if isinstance(estado, Enum):
        return str(estado.value)
    return str(estado)


def _es_estado(factura, estado: EstadoFactura) -> bool:
    return _valor_estado(getattr(factura, "estado", None)) == estado.value


def _es_facturable(factura) -> bool:
    return _valor_estado(getattr(factura, "estado", None)) in ESTADOS_FACTURABLES


def _dinero(valor) -> str:
    return str(Decimal(str(valor)).quantize(CENTAVOS))


def _rango(anio, mes) -> tuple[date | None, date | None]:
    if anio and mes:
        anio, mes = int(anio), int(mes)
        ultimo = calendar.monthrange(anio, mes)[1]
        return date(anio, mes, 1), date(anio, mes, ultimo)
    if anio:
        anio = int(anio)
        return date(anio, 1, 1), date(anio, 12, 31)
    return None, None


def _facturas(
    db,
    *,
    anio=None,
    mes=None,
    cliente=None,
    estado: EstadoFactura | None = None,
    solo_facturables: bool = False,
):
    desde, hasta = _rango(anio, mes)
    resultados = FacturaRepository.listar(
        db,
        estado=estado,
        fecha_desde=desde,
        fecha_hasta=hasta,
        cliente=cliente,
        limit=LIMITE,
    )
    if solo_facturables:
        resultados = [f for f in resultados if _es_facturable(f)]
    return resultados


def _mes_de(fecha) -> str:
    if hasattr(fecha, "strftime"):
        return fecha.strftime("%Y-%m")
    return str(fecha)[:7]


def _fila_factura(factura) -> dict:
    return {
        "numero_serie": factura.numero_serie,
        "fecha": str(factura.fecha),
        "cliente": factura.cliente_nombre,
        "total": _dinero(factura.total),
        "estado": _valor_estado(factura.estado),
    }


def _filtros(anio, mes, cliente) -> dict:
    return {"anio": anio, "mes": mes, "cliente": cliente}


def ventas_por_mes(db, *, anio=None, mes=None, cliente=None) -> dict:
    facturas = _facturas(
        db, anio=anio, mes=mes, cliente=cliente, solo_facturables=True
    )
    totales = defaultdict(lambda: Decimal("0.00"))
    cantidades = defaultdict(int)
    for factura in facturas:
        clave = _mes_de(factura.fecha)
        totales[clave] += Decimal(str(factura.total))
        cantidades[clave] += 1

    datos = [
        {
            "mes": clave,
            "total": _dinero(totales[clave]),
            "facturas": cantidades[clave],
        }
        for clave in sorted(totales)
    ]
    return {
        "consulta": "ventas_por_mes",
        "filtros": _filtros(anio, mes, cliente),
        "datos": datos,
        "total": _dinero(sum(totales.values(), Decimal("0.00"))),
        "detalle": f"{len(facturas)} facturas facturables en {len(datos)} meses",
    }


def ventas_por_cliente(db, *, anio=None, mes=None, cliente=None) -> dict:
    facturas = _facturas(
        db, anio=anio, mes=mes, cliente=cliente, solo_facturables=True
    )
    totales = defaultdict(lambda: Decimal("0.00"))
    cantidades = defaultdict(int)
    for factura in facturas:
        nombre = factura.cliente_nombre or "(sin cliente)"
        totales[nombre] += Decimal(str(factura.total))
        cantidades[nombre] += 1

    datos = [
        {
            "cliente": nombre,
            "total": _dinero(totales[nombre]),
            "facturas": cantidades[nombre],
        }
        for nombre in sorted(totales)
    ]
    return {
        "consulta": "ventas_por_cliente",
        "filtros": _filtros(anio, mes, cliente),
        "datos": datos,
        "total": _dinero(sum(totales.values(), Decimal("0.00"))),
        "detalle": f"{len(datos)} clientes con facturas facturables",
    }


def ventas_por_producto(db, *, anio=None, mes=None, cliente=None) -> dict:
    facturas = _facturas(
        db, anio=anio, mes=mes, cliente=cliente, solo_facturables=True
    )
    totales = defaultdict(lambda: Decimal("0.00"))
    unidades = defaultdict(lambda: Decimal("0.00"))
    for factura in facturas:
        for linea in getattr(factura, "lineas", ()):
            nombre = getattr(linea, "descripcion", None) or "(sin descripción)"
            totales[nombre] += Decimal(str(getattr(linea, "monto", "0")))
            unidades[nombre] += Decimal(str(getattr(linea, "cantidad", "0")))

    datos = [
        {
            "producto": nombre,
            "unidades": _dinero(unidades[nombre]),
            "total": _dinero(totales[nombre]),
        }
        for nombre in sorted(totales)
    ]
    return {
        "consulta": "ventas_por_producto",
        "filtros": _filtros(anio, mes, cliente),
        "datos": datos,
        "total": _dinero(sum(totales.values(), Decimal("0.00"))),
        "detalle": f"{len(datos)} productos vendidos",
    }


def facturas_anuladas(db, *, anio=None, mes=None, cliente=None) -> dict:
    facturas = _facturas(
        db,
        anio=anio,
        mes=mes,
        cliente=cliente,
        estado=EstadoFactura.ANULADA,
    )
    return {
        "consulta": "facturas_anuladas",
        "filtros": _filtros(anio, mes, cliente),
        "datos": [_fila_factura(factura) for factura in facturas],
        "cantidad": len(facturas),
        "detalle": f"{len(facturas)} facturas anuladas",
    }


def facturas_en_revision(db, *, anio=None, mes=None, cliente=None) -> dict:
    facturas = _facturas(
        db,
        anio=anio,
        mes=mes,
        cliente=cliente,
        estado=EstadoFactura.EN_REVISION,
    )
    return {
        "consulta": "facturas_en_revision",
        "filtros": _filtros(anio, mes, cliente),
        "datos": [_fila_factura(factura) for factura in facturas],
        "cantidad": len(facturas),
        "detalle": f"{len(facturas)} facturas en revisión",
    }


def top_productos(db, *, n=5, anio=None, mes=None, cliente=None) -> dict:
    facturas = _facturas(
        db, anio=anio, mes=mes, cliente=cliente, solo_facturables=True
    )
    unidades = defaultdict(lambda: Decimal("0.00"))
    totales = defaultdict(lambda: Decimal("0.00"))
    for factura in facturas:
        for linea in getattr(factura, "lineas", ()):
            nombre = getattr(linea, "descripcion", None) or "(sin descripción)"
            unidades[nombre] += Decimal(str(getattr(linea, "cantidad", "0")))
            totales[nombre] += Decimal(str(getattr(linea, "monto", "0")))

    n = max(1, min(int(n), 20))
    ordenados = sorted(
        unidades, key=lambda nombre: (unidades[nombre], totales[nombre]), reverse=True
    )[:n]
    datos = [
        {
            "producto": nombre,
            "unidades": _dinero(unidades[nombre]),
            "total": _dinero(totales[nombre]),
        }
        for nombre in ordenados
    ]
    return {
        "consulta": "top_productos",
        "filtros": _filtros(anio, mes, cliente) | {"n": n},
        "datos": datos,
        "detalle": f"top {n} por unidades (sin modelo entrenado)",
    }


CATALOGO = {
    "ventas_por_mes": ventas_por_mes,
    "ventas_por_cliente": ventas_por_cliente,
    "ventas_por_producto": ventas_por_producto,
    "facturas_anuladas": facturas_anuladas,
    "top_productos": top_productos,
    "facturas_en_revision": facturas_en_revision,
}
