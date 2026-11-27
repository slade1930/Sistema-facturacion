"""Catálogo de consultas del asistente (paso 0; se arma en el paso 4).

Módulo app.ml.asistente. Dueño: Fernando (Módulo 4). Depende de los repositorios existentes.
Seis consultas predefinidas, nunca SQL generado.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from app.models.facturacion import EstadoFactura
from app.repositories.catalogo import ClienteB2BRepository
from app.repositories.facturacion import FacturaRepository

LIMITE = 10_000
CENTAVOS = Decimal("0.01")
NOTA_PRODUCTOS = (
    "suma montos netos de línea, sin ITBMS ni portes; agrupa por producto_id cuando existe"
)

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
    return str(Decimal(str(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP))


def _fecha(valor):
    if valor is None:
        return None
    if hasattr(valor, "year"):
        return valor
    return date.fromisoformat(str(valor))


def _rango(anio=None, mes=None, dia=None, desde=None, hasta=None):
    if desde is not None or hasta is not None:
        return _fecha(desde), _fecha(hasta)
    if anio and mes and dia:
        fecha = date(int(anio), int(mes), int(dia))
        return fecha, fecha
    if anio and mes:
        anio, mes = int(anio), int(mes)
        ultimo = calendar.monthrange(anio, mes)[1]
        return date(anio, mes, 1), date(anio, mes, ultimo)
    if anio:
        anio = int(anio)
        return date(anio, 1, 1), date(anio, 12, 31)
    if mes:
        hoy = date.today()
        mes = int(mes)
        ultimo = calendar.monthrange(hoy.year, mes)[1]
        return date(hoy.year, mes, 1), date(hoy.year, mes, ultimo)
    return None, None


def _facturas(
    db,
    *,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
    estado=None,
    solo_facturables=False,
):
    nota = None
    if cliente_id is not None:
        registro = ClienteB2BRepository(db).get(int(cliente_id))
        if registro is None:
            return [], False, f"cliente {cliente_id} no existe"
        cliente = registro.nombre_empresa

    fecha_desde, fecha_hasta = _rango(anio, mes, dia, desde, hasta)
    resultados = FacturaRepository.listar(
        db,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        limit=LIMITE + 1,
    )
    truncado = len(resultados) > LIMITE
    if truncado:
        resultados = resultados[:LIMITE]
    if solo_facturables:
        resultados = [f for f in resultados if _es_facturable(f)]
    return resultados, truncado, nota


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


def _filtros(
    anio=None,
    mes=None,
    cliente=None,
    *,
    cliente_id=None,
    dia=None,
    desde=None,
    hasta=None,
    n=None,
) -> dict:
    filtros = {"anio": anio, "mes": mes, "cliente": cliente}
    if cliente_id is not None:
        filtros["cliente_id"] = cliente_id
    if dia is not None:
        filtros["dia"] = dia
    if desde is not None:
        filtros["desde"] = str(desde)
    if hasta is not None:
        filtros["hasta"] = str(hasta)
    if n is not None:
        filtros["n"] = n
    return filtros


def _clave_producto(linea):
    producto_id = getattr(linea, "producto_id", None)
    descripcion = getattr(linea, "descripcion", None) or "(sin descripción)"
    return (int(producto_id) if producto_id is not None else None, descripcion)


def _detalle(texto, nota) -> str:
    return f"{texto}; {nota}" if nota else texto


def ventas_por_mes(
    db,
    *,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
) -> dict:
    facturas, truncado, nota = _facturas(
        db,
        anio=anio,
        mes=mes,
        dia=dia,
        desde=desde,
        hasta=hasta,
        cliente=cliente,
        cliente_id=cliente_id,
        solo_facturables=True,
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
        "filtros": _filtros(anio, mes, cliente, cliente_id=cliente_id, dia=dia, desde=desde, hasta=hasta),
        "datos": datos,
        "total": _dinero(sum(totales.values(), Decimal("0.00"))),
        "truncado": truncado,
        "detalle": _detalle(
            f"{len(facturas)} facturas facturables en {len(datos)} meses", nota
        ),
    }


def ventas_por_cliente(
    db,
    *,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
) -> dict:
    facturas, truncado, nota = _facturas(
        db,
        anio=anio,
        mes=mes,
        dia=dia,
        desde=desde,
        hasta=hasta,
        cliente=cliente,
        cliente_id=cliente_id,
        solo_facturables=True,
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
        "filtros": _filtros(anio, mes, cliente, cliente_id=cliente_id, dia=dia, desde=desde, hasta=hasta),
        "datos": datos,
        "total": _dinero(sum(totales.values(), Decimal("0.00"))),
        "truncado": truncado,
        "detalle": _detalle(
            f"{len(datos)} clientes con facturas facturables", nota
        ),
    }


def ventas_por_producto(
    db,
    *,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
) -> dict:
    facturas, truncado, nota = _facturas(
        db,
        anio=anio,
        mes=mes,
        dia=dia,
        desde=desde,
        hasta=hasta,
        cliente=cliente,
        cliente_id=cliente_id,
        solo_facturables=True,
    )
    totales = defaultdict(lambda: Decimal("0.00"))
    unidades = defaultdict(lambda: Decimal("0.00"))
    nombres = {}
    for factura in facturas:
        for linea in getattr(factura, "lineas", ()):
            clave = _clave_producto(linea)
            nombres[clave] = clave[1]
            totales[clave] += Decimal(str(getattr(linea, "monto", "0")))
            unidades[clave] += Decimal(str(getattr(linea, "cantidad", "0")))

    datos = [
        {
            "producto_id": clave[0],
            "producto": nombres[clave],
            "unidades": _dinero(unidades[clave]),
            "total": _dinero(totales[clave]),
        }
        for clave in sorted(totales, key=lambda c: (nombres[c], c[0] or 0))
    ]
    return {
        "consulta": "ventas_por_producto",
        "filtros": _filtros(anio, mes, cliente, cliente_id=cliente_id, dia=dia, desde=desde, hasta=hasta),
        "datos": datos,
        "total": _dinero(sum(totales.values(), Decimal("0.00"))),
        "truncado": truncado,
        "nota": NOTA_PRODUCTOS,
        "detalle": _detalle(f"{len(datos)} productos vendidos", nota),
    }


def facturas_anuladas(
    db,
    *,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
) -> dict:
    facturas, truncado, nota = _facturas(
        db,
        anio=anio,
        mes=mes,
        dia=dia,
        desde=desde,
        hasta=hasta,
        cliente=cliente,
        cliente_id=cliente_id,
        estado=EstadoFactura.ANULADA,
    )
    return {
        "consulta": "facturas_anuladas",
        "filtros": _filtros(anio, mes, cliente, cliente_id=cliente_id, dia=dia, desde=desde, hasta=hasta),
        "datos": [_fila_factura(factura) for factura in facturas],
        "cantidad": len(facturas),
        "truncado": truncado,
        "detalle": _detalle(f"{len(facturas)} facturas anuladas", nota),
    }


def facturas_en_revision(
    db,
    *,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
) -> dict:
    facturas, truncado, nota = _facturas(
        db,
        anio=anio,
        mes=mes,
        dia=dia,
        desde=desde,
        hasta=hasta,
        cliente=cliente,
        cliente_id=cliente_id,
        estado=EstadoFactura.EN_REVISION,
    )
    return {
        "consulta": "facturas_en_revision",
        "filtros": _filtros(anio, mes, cliente, cliente_id=cliente_id, dia=dia, desde=desde, hasta=hasta),
        "datos": [_fila_factura(factura) for factura in facturas],
        "cantidad": len(facturas),
        "truncado": truncado,
        "detalle": _detalle(f"{len(facturas)} facturas en revisión", nota),
    }


def top_productos(
    db,
    *,
    n=5,
    anio=None,
    mes=None,
    dia=None,
    desde=None,
    hasta=None,
    cliente=None,
    cliente_id=None,
) -> dict:
    facturas, truncado, nota = _facturas(
        db,
        anio=anio,
        mes=mes,
        dia=dia,
        desde=desde,
        hasta=hasta,
        cliente=cliente,
        cliente_id=cliente_id,
        solo_facturables=True,
    )
    unidades = defaultdict(lambda: Decimal("0.00"))
    totales = defaultdict(lambda: Decimal("0.00"))
    nombres = {}
    for factura in facturas:
        for linea in getattr(factura, "lineas", ()):
            clave = _clave_producto(linea)
            nombres[clave] = clave[1]
            unidades[clave] += Decimal(str(getattr(linea, "cantidad", "0")))
            totales[clave] += Decimal(str(getattr(linea, "monto", "0")))

    n = min(max(0, int(n)), 20)
    ordenados = sorted(
        unidades, key=lambda c: (unidades[c], totales[c]), reverse=True
    )[:n]
    datos = [
        {
            "producto_id": clave[0],
            "producto": nombres[clave],
            "unidades": _dinero(unidades[clave]),
            "total": _dinero(totales[clave]),
        }
        for clave in ordenados
    ]
    return {
        "consulta": "top_productos",
        "filtros": _filtros(
            anio, mes, cliente, cliente_id=cliente_id, dia=dia, desde=desde, hasta=hasta, n=n
        ),
        "datos": datos,
        "truncado": truncado,
        "nota": NOTA_PRODUCTOS,
        "detalle": _detalle(f"top {n} por unidades (sin modelo entrenado)", nota),
    }


CATALOGO = {
    "ventas_por_mes": ventas_por_mes,
    "ventas_por_cliente": ventas_por_cliente,
    "ventas_por_producto": ventas_por_producto,
    "facturas_anuladas": facturas_anuladas,
    "top_productos": top_productos,
    "facturas_en_revision": facturas_en_revision,
}
