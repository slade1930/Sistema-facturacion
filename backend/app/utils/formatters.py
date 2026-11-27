"""Formateo de presentación: moneda, fechas y textos auxiliares.

Funciones puras (str/Decimal/date -> str), sin dependencias externas.
Los montos se normalizan con Decimal + ROUND_HALF_UP a 2 decimales,
igual que en services/totales.py.
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Union

from app.utils.validators import a_decimal

CENTAVO = Decimal("0.01")

FechaLike = Union[date, datetime, str, None]


def _decimal_centavos(monto) -> Decimal:
    return a_decimal(monto, "monto").quantize(CENTAVO, rounding=ROUND_HALF_UP)


def formato_moneda(monto, moneda: str = "") -> str:
    """1234.5 -> '1,234.50'; con signo si es negativo.

    El quantize HALF_UP se hace ANTES de formatear para que el redondeo
    sea el del sistema y no el del format spec (que usa half-even).
    """
    d = _decimal_centavos(monto)
    signo = "-" if d < 0 else ""
    texto = f"{signo}{abs(d):,.2f}"
    return f"{texto} {moneda}".strip() if moneda else texto


def formato_porcentaje(valor, decimales: int = 2) -> str:
    """Decimal('7') -> '7.00%'; redondeo HALF_UP como el resto del sistema."""
    d = a_decimal(valor, "porcentaje")
    paso = Decimal(1).scaleb(-decimales)
    d = d.quantize(paso, rounding=ROUND_HALF_UP)
    return f"{d}%"


def formato_fecha(fecha: FechaLike) -> str:
    """date/datetime -> 'DD/MM/YYYY'. Acepta str ISO y la devuelve igual."""
    if fecha is None:
        return ""
    if isinstance(fecha, str):
        return fecha
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year:04d}"


def formato_fecha_hora(fecha: FechaLike) -> str:
    """datetime -> 'DD/MM/YYYY HH:MM'. date solo -> 'DD/MM/YYYY'."""
    if not isinstance(fecha, datetime):
        return formato_fecha(fecha)
    return f"{formato_fecha(fecha)} {fecha.hour:02d}:{fecha.minute:02d}"


def formato_ruc(ruc) -> str:
    """RUC solo dígitos/guiones normalizados: quita espacios y devuelve str."""
    if ruc is None:
        return ""
    return str(ruc).strip()
