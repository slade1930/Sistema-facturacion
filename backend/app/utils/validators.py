"""Validaciones de soporte: series, líneas, montos y parámetros.

Todas las funciones de validación lanzan ValueError con un mensaje claro.
Los montos se manejan con Decimal, nunca con float.

RUTA OFICIAL de validadores del proyecto. Importar siempre desde
app.utils.validators.
"""

import re
from decimal import Decimal, InvalidOperation

# Coincide con String(20) de Factura.numero_serie
LONGITUD_MAX_SERIE = 20

PATRON_FACTURA = re.compile(r"^FAC-(\d{4})-(\d{4,})$")
PATRON_ORDEN_COMPRA = re.compile(r"^OC-(\d{4})-(\d{4,})$")

__all__ = [
    "LONGITUD_MAX_SERIE",
    "PATRON_FACTURA",
    "PATRON_ORDEN_COMPRA",
    "es_serie_factura_valida",
    "es_serie_oc_valida",
    "extraer_anio",
    "a_decimal",
    "validar_cantidad",
    "validar_precio",
    "validar_descuento_pct",
    "validar_unidades_por_caja",
    "validar_linea",
    "validar_lineas",
]


# ---------- Series ----------

def es_serie_factura_valida(serie: str) -> bool:
    """True si tiene el formato FAC-AAAA-0001 (y cabe en 20 caracteres)."""
    return (
        isinstance(serie, str)
        and len(serie) <= LONGITUD_MAX_SERIE
        and bool(PATRON_FACTURA.match(serie))
    )


def es_serie_oc_valida(serie: str) -> bool:
    """True si tiene el formato OC-AAAA-0001 (y cabe en 20 caracteres)."""
    return (
        isinstance(serie, str)
        and len(serie) <= LONGITUD_MAX_SERIE
        and bool(PATRON_ORDEN_COMPRA.match(serie))
    )


def extraer_anio(serie: str) -> int:
    """Devuelve el año de un folio FAC-AAAA-0001 u OC-AAAA-0001."""
    for patron in (PATRON_FACTURA, PATRON_ORDEN_COMPRA):
        m = patron.match(serie or "")
        if m:
            return int(m.group(1))
    raise ValueError(f"Serie con formato inválido: {serie!r}")


# ---------- Montos y parámetros ----------

def a_decimal(valor, campo: str = "valor") -> Decimal:
    """Convierte a Decimal. Rechaza None, texto no numérico, NaN e infinito."""
    if valor is None or isinstance(valor, bool):
        raise ValueError(f"{campo} es obligatorio y debe ser numérico")
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{campo} no es un número válido: {valor!r}")
    if not d.is_finite():
        raise ValueError(f"{campo} no es un número válido: {valor!r}")
    return d


def validar_cantidad(cantidad) -> Decimal:
    d = a_decimal(cantidad, "cantidad")
    if d < Decimal("0.01"):  # ck_linea_factura_cantidad
        raise ValueError("La cantidad debe ser al menos 0.01")
    return d


def validar_precio(precio, campo: str = "precio_unitario") -> Decimal:
    d = a_decimal(precio, campo)
    if d < 0:
        raise ValueError(f"{campo} no puede ser negativo")
    return d


def validar_descuento_pct(descuento) -> Decimal:
    d = a_decimal(descuento, "descuento_pct")
    if d < 0 or d > 100:
        raise ValueError("El descuento debe estar entre 0 y 100")
    return d


def validar_unidades_por_caja(unidades) -> int:
    if isinstance(unidades, bool) or not isinstance(unidades, int):
        raise ValueError("unidades_por_caja debe ser un entero")
    if unidades < 1:  # ck_linea_factura_unidades
        raise ValueError("unidades_por_caja debe ser al menos 1")
    return unidades


# ---------- Líneas y documentos ----------

def _obtener(linea, campo, defecto=None):
    """Lee un campo de una línea que sea dict u objeto."""
    if isinstance(linea, dict):
        return linea.get(campo, defecto)
    return getattr(linea, campo, defecto)


def validar_linea(linea) -> None:
    """Valida cantidad, precio, descuento y unidades por caja de una línea."""
    validar_cantidad(_obtener(linea, "cantidad"))
    validar_precio(_obtener(linea, "precio_unitario"))
    validar_descuento_pct(_obtener(linea, "descuento_pct", 0))
    validar_unidades_por_caja(_obtener(linea, "unidades_por_caja", 1))


def validar_lineas(lineas) -> None:
    """Exige al menos una línea y que todas sean válidas."""
    if not lineas:
        raise ValueError("El documento necesita al menos una línea")
    for i, linea in enumerate(lineas, start=1):
        try:
            validar_linea(linea)
        except ValueError as e:
            raise ValueError(f"Línea {i}: {e}")
