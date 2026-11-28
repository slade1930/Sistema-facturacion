"""Formato de datos del backend para la interfaz; etapa C2."""

from decimal import Decimal, InvalidOperation
from typing import Any

VACIO = "—"


def dinero(valor: Any) -> str:
    """Muestra el importe que entregó el backend sin redondearlo de otro modo."""
    if valor is None or str(valor).strip() == "":
        return VACIO
    texto = str(valor).strip()
    try:
        numero = Decimal(texto)
    except (InvalidOperation, ValueError, TypeError):
        return texto
    plano = format(numero, "f")
    signo = ""
    if plano.startswith("-"):
        signo, plano = "-", plano[1:]
    if "." in plano:
        entero, decimales = plano.split(".", 1)
        decimales = decimales.ljust(2, "0")
    else:
        entero, decimales = plano, "00"
    return f"{signo}{entero}.{decimales}"


def numero(valor: Any) -> float:
    """Solo para ejes de gráficos: el backend ya entregó la cifra final."""
    try:
        return float(Decimal(str(valor or 0)))
    except (InvalidOperation, ValueError, TypeError):
        return 0.0


def fecha(valor: Any) -> str:
    """Fecha ISO del backend, sin cambiar de zona horaria."""
    texto = str(valor or "").strip()
    if not texto:
        return VACIO
    return texto[:10] if "T" in texto else texto


def texto(valor: Any) -> str:
    if valor is None or str(valor).strip() == "":
        return VACIO
    return str(valor)


__all__ = ["VACIO", "dinero", "fecha", "numero", "texto"]
