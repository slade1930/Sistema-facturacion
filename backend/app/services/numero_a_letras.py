"""Conversión de montos a letras en español para la factura.

Sin dependencias externas (num2words NO está en requirements.txt).
Todo el dinero entra como Decimal/int/str y se normaliza con
ROUND_HALF_UP a 2 decimales, igual que el resto del sistema.

Formato de salida:
- numero_a_letras(1234.56)        -> "mil doscientos treinta y cuatro con 56/100"
- monto_a_letras_factura(1234.56) -> "SON: MIL DOSCIENTOS TREINTA Y CUATRO CON 56/100"

Tope: Numeric(14, 2) del esquema = 999,999,999,999.99. Montos mayores
lanzan ValueError en vez de producir un texto incorrecto.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.utils.validators import a_decimal

CENTAVO = Decimal("0.01")
# Numeric(14,2): 12 dígitos enteros + 2 decimales
_MAX_ENTERO = 999_999_999_999

# 0-29 con las formas correctas (veintiún, veintidós, veintitrés, ...)
_CHICOS = [
    "", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
    "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
    "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte",
    "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
    "veintiséis", "veintisiete", "veintiocho", "veintinueve",
]

_DECENAS = {
    30: "treinta", 40: "cuarenta", 50: "cincuenta",
    60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa",
}

_CENTENAS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos",
    "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos",
]


def _decenas(n: int) -> str:
    """30-99: 'treinta y cinco', 'ochenta y nueve'."""
    d, u = divmod(n, 10)
    return _DECENAS[d * 10] + (f" y {_CHICOS[u]}" if u else "")


def _bajo_mil(n: int) -> str:
    """0-999 en letras. 0 devuelve cadena vacía (lo decide quien llama)."""
    if n == 0:
        return ""
    if n < 30:
        return _CHICOS[n]
    if n < 100:
        return _decenas(n)
    if n == 100:
        return "cien"
    c, r = divmod(n, 100)
    partes = ["ciento" if c == 1 else _CENTENAS[c]]
    if r:
        partes.append(_CHICOS[r] if r < 30 else _decenas(r))
    return " ".join(partes)


def _entero_a_letras(n: int) -> str:
    """Entero no negativo hasta 999,999,999,999 en letras."""
    if n == 0:
        return "cero"
    partes = []
    mil_millones, resto = divmod(n, 1_000_000_000)
    millones, resto = divmod(resto, 1_000_000)
    miles, resto = divmod(resto, 1_000)
    if mil_millones:
        # 1e9 exacto es "mil millones", no "uno mil millones"
        partes.append(
            "mil millones"
            if mil_millones == 1
            else f"{_bajo_mil(mil_millones)} mil millones"
        )
    if millones:
        partes.append("un millón" if millones == 1 else f"{_bajo_mil(millones)} millones")
    if miles:
        partes.append("mil" if miles == 1 else f"{_bajo_mil(miles)} mil")
    if resto:
        partes.append(_bajo_mil(resto))
    return " ".join(partes)


def _partes_monto(monto) -> tuple[str, int]:
    """Normaliza el monto y devuelve (letras del entero, centavos 0-99)."""
    d = a_decimal(monto, "monto").quantize(CENTAVO, rounding=ROUND_HALF_UP)
    if d < 0:
        raise ValueError("El monto no puede ser negativo")
    entero = int(d)
    if entero > _MAX_ENTERO:
        raise ValueError(
            f"El monto {d} excede el máximo del esquema (Numeric(14,2))"
        )
    centavos = int((d - entero) * 100)
    return _entero_a_letras(entero), centavos


def numero_a_letras(monto) -> str:
    """Decimal -> 'mil doscientos treinta y cuatro con 56/100'.

    Ojo: el redondeo HALF_UP puede subir el entero (99.999 -> 'cien con 00/100').
    """
    letras, centavos = _partes_monto(monto)
    return f"{letras} con {centavos:02d}/100"


def monto_a_letras_factura(monto, prefijo: str = "SON") -> str:
    """Formato de factura: 'SON: MIL DOSCIENTOS ... CON 56/100'."""
    letras, centavos = _partes_monto(monto)
    return f"{prefijo}: {letras.upper()} CON {centavos:02d}/100"
