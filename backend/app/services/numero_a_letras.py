"""Conversión de montos a letras en español para la factura.

Sin dependencias externas. Los montos se normalizan a 2 decimales con
ROUND_HALF_UP.

Ejemplos:
- numero_a_letras(1234.56) -> "mil doscientos treinta y cuatro con 56/100"
- monto_a_letras_factura(1234.56) -> "SON: MIL DOSCIENTOS TREINTA Y CUATRO CON 56/100"

Tope: Numeric(14, 2) = 999,999,999,999.99. Montos mayores lanzan ValueError.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTAVO = Decimal("0.01")
_MAX_MONTO = Decimal("999999999999.99")

_UNIDADES = [
    "", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
    "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
    "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte",
    "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
    "veintiséis", "veintisiete", "veintiocho", "veintinueve",
]

_DECENAS = {
    30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta",
    70: "setenta", 80: "ochenta", 90: "noventa",
}

_CENTENAS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos",
    "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos",
]


def _a_decimal(valor) -> Decimal:
    """Convierte int, str, float o Decimal a Decimal finito."""
    if isinstance(valor, bool):
        raise ValueError("El monto no puede ser booleano")
    try:
        dec = Decimal(str(valor).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Monto inválido: {valor!r}") from exc
    if not dec.is_finite():
        raise ValueError(f"Monto inválido: {valor!r}")
    return dec


def _decenas(n: int) -> str:
    """30-99: 'treinta y cinco', 'ochenta y nueve'."""
    d, u = divmod(n, 10)
    return _DECENAS[d * 10] + (f" y {_UNIDADES[u]}" if u else "")


def _bajo_mil(n: int) -> str:
    """0-999 en letras. Devuelve cadena vacía para 0."""
    if n == 0:
        return ""
    if n < 30:
        return _UNIDADES[n]
    if n < 100:
        return _decenas(n)
    if n == 100:
        return "cien"
    c, r = divmod(n, 100)
    return _CENTENAS[c] + (f" {_bajo_mil(r)}" if r else "")


def _apocopar(texto: str) -> str:
    """Ajusta 'uno' a 'un' cuando precede a millón, mil o millones."""
    if texto.endswith("veintiuno"):
        return texto[:-3] + "ún"
    if texto.endswith(" uno"):
        return texto[:-4] + " un"
    return texto


def _entero(n: int) -> str:
    """0 a 999,999,999,999 en letras."""
    if n == 0:
        return "cero"

    partes = []

    mm, n = divmod(n, 1_000_000_000)
    if mm == 1:
        partes.append("mil millones")
    elif mm > 1:
        partes.append(f"{_apocopar(_entero(mm))} mil millones")

    mi, n = divmod(n, 1_000_000)
    if mi == 1:
        partes.append("un millón")
    elif mi > 1:
        partes.append(f"{_apocopar(_entero(mi))} millones")

    miles, n = divmod(n, 1000)
    if miles == 1:
        partes.append("mil")
    elif miles > 1:
        partes.append(f"{_apocopar(_bajo_mil(miles))} mil")

    if n:
        partes.append(_bajo_mil(n))

    return " ".join(partes)


def numero_a_letras(valor) -> str:
    """Convierte un monto a letras con centavos en formato 'NN/100'."""
    monto = _a_decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)

    if monto < 0:
        raise ValueError("El monto no puede ser negativo")
    if monto > _MAX_MONTO:
        raise ValueError("El monto excede el tope de 999,999,999,999.99")

    entero = int(monto)
    centavos = int(monto * 100) % 100
    return f"{_entero(entero)} con {centavos:02d}/100"


def monto_a_letras_factura(valor) -> str:
    """Formato para factura: 'SON: ...' en mayúsculas."""
    return f"SON: {numero_a_letras(valor).upper()}"
