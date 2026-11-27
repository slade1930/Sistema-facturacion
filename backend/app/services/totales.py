"""Gente, acá calculamos los totales de la factura con Decimal y ROUND_HALF_UP.

Reglas del esquema del proyecto:

- El precio a cobrar sale del renglón: si `cobrar_por` es "caja" usamos
  `precio_unitario` completo; si es "unidad" usamos `precio_unidad` cuando
  viene con valor, y si no, también `precio_unitario`. No dividimos entre
  `unidades_por_caja`: ese campo solo describe el empaque.
- El monto de la línea se calcula en una sola operación: bruto por el factor
  (100 - descuento) / 100, y se redondea una sola vez al final a dos
  decimales. Nada de redondear el bruto y el descuento por separado.
- `subtotal`: si hay descuentos mostramos la suma de los brutos y el
  descuento aparte, para que `subtotal - descuento_total = base` cuadre al
  centavo. Si no hay descuentos, `subtotal` es directamente la base.
- `base_gravada` y `base_exenta` suman los montos ya redondeados de cada
  línea; el ITBMS es 7 % solo de la base gravada.
- `total` = base gravada + base exenta + ITBMS + portes. Los portes no
  generan ITBMS y no pueden ser negativos.

Las validaciones de cantidad, precio, descuento y unidades por caja vienen
de `app.utils.validators`, la ruta oficial de validadores.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Mapping, MutableMapping

from app.utils.validators import (
    a_decimal,
    validar_cantidad,
    validar_descuento_pct,
    validar_precio,
)

CENTAVO = Decimal("0.01")
CERO = Decimal("0.00")
CIEN = Decimal("100")
TASA_ITBMS = Decimal("0.07")

COBRAR_POR_UNIDAD = "unidad"
COBRAR_POR_CAJA = "caja"


def _a_centavos(valor: Decimal) -> Decimal:
    """Gente, redondeo a dos decimales con ROUND_HALF_UP: el .005 siempre sube."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _campo(linea: Any, nombre: str, defecto: Any = None) -> Any:
    """Lee un campo de una línea que sea dict u objeto ORM."""
    if isinstance(linea, Mapping):
        return linea.get(nombre, defecto)
    return getattr(linea, nombre, defecto)


def _datos_linea(linea: Any) -> tuple[Decimal, Decimal, Decimal, bool]:
    """Devuelve cantidad, precio a cobrar, descuento y si es gravada.

    Lanza ValueError si la línea no cumple las reglas del esquema.
    """
    cantidad = validar_cantidad(_campo(linea, "cantidad"))
    precio = validar_precio(_campo(linea, "precio_unitario"))

    cobrar_por = _campo(linea, "cobrar_por", COBRAR_POR_UNIDAD)
    if cobrar_por is None:
        cobrar_por = COBRAR_POR_UNIDAD
    if str(cobrar_por) != COBRAR_POR_CAJA:
        precio_unidad = _campo(linea, "precio_unidad")
        if precio_unidad is not None:
            precio_unidad = validar_precio(precio_unidad, "precio_unidad")
            if precio_unidad > CERO:
                precio = precio_unidad

    descuento_raw = _campo(linea, "descuento_pct")
    descuento_pct = (
        CERO if descuento_raw is None else validar_descuento_pct(descuento_raw)
    )

    gravada = _campo(linea, "gravada", True)
    if gravada is None:
        gravada = True

    return cantidad, precio, descuento_pct, bool(gravada)


def _bruto_exacto(linea: Any) -> Decimal:
    """Cantidad por el precio a cobrar, todavía sin redondear."""
    cantidad, precio, _, _ = _datos_linea(linea)
    return cantidad * precio


def _monto_desde_bruto(bruto: Decimal, descuento_pct: Decimal) -> Decimal:
    """Aplica el descuento y redondea una sola vez, al final."""
    if descuento_pct >= CIEN:
        return CERO
    if descuento_pct > CERO:
        return _a_centavos(bruto * (CIEN - descuento_pct) / CIEN)
    return _a_centavos(bruto)


def calcular_monto_linea(linea: Any) -> Decimal:
    """Devuelve el monto neto de una línea (cantidad x precio - descuento).

    Acepta LineaFactura (ORM) o dict con las mismas claves.
    """
    cantidad, precio, descuento_pct, _ = _datos_linea(linea)
    return _monto_desde_bruto(cantidad * precio, descuento_pct)


def calcular_bruto_linea(linea: Any) -> Decimal:
    """Devuelve cantidad x precio a cobrar sin descontar, a dos decimales."""
    return _a_centavos(_bruto_exacto(linea))


def calcular_totales(
    lineas: Iterable[Any], portes: Any = Decimal("0.00")
) -> dict[str, Decimal]:
    """Calcula los campos de totales de Factura a partir de sus líneas.

    `portes` acepta Decimal, int, float o str numérico; None cuenta como 0.
    Devuelve dict con subtotal, descuento_total, base_gravada, base_exenta,
    itbms y total (todos Decimal con dos decimales).
    """
    subtotal = CERO
    descuento_total = CERO
    base_gravada = CERO
    base_exenta = CERO
    suma_bruta = Decimal("0")
    hay_descuentos = False

    for linea in lineas or []:
        cantidad, precio, descuento_pct, gravada = _datos_linea(linea)
        bruto = cantidad * precio
        monto = _monto_desde_bruto(bruto, descuento_pct)

        suma_bruta += bruto
        if descuento_pct > CERO:
            hay_descuentos = True

        if gravada:
            base_gravada += monto
        else:
            base_exenta += monto

    base_gravada = _a_centavos(base_gravada)
    base_exenta = _a_centavos(base_exenta)
    base = base_gravada + base_exenta

    if hay_descuentos:
        subtotal = _a_centavos(suma_bruta)
        descuento_total = _a_centavos(subtotal - base)
        if descuento_total < CERO:
            descuento_total = CERO
    else:
        subtotal = base
        descuento_total = CERO

    itbms = _a_centavos(base_gravada * TASA_ITBMS)

    portes_dec = CERO if portes is None else a_decimal(portes, "portes")
    if portes_dec < 0:
        raise ValueError("portes no puede ser negativo")
    portes_dec = _a_centavos(portes_dec)

    total = _a_centavos(base + itbms + portes_dec)

    return {
        "subtotal": _a_centavos(subtotal),
        "descuento_total": _a_centavos(descuento_total),
        "base_gravada": base_gravada,
        "base_exenta": base_exenta,
        "itbms": itbms,
        "total": total,
    }


def aplicar_totales(factura: MutableMapping[str, Any] | Any) -> dict[str, Decimal]:
    """Calcula totales y los escribe en la factura (objeto ORM o dict).

    También rellena `monto` en cada línea de `factura.lineas` cuando la
    línea todavía no lo tiene, para que el INSERT respete el cálculo.
    No hace commit: la transacción la maneja quien llama.
    """
    lineas = _campo(factura, "lineas", []) or []
    totales = calcular_totales(lineas, _campo(factura, "portes", Decimal("0.00")))

    for nombre, valor in totales.items():
        if isinstance(factura, MutableMapping):
            factura[nombre] = valor
        else:
            setattr(factura, nombre, valor)

    for linea in lineas:
        monto = calcular_monto_linea(linea)
        if isinstance(linea, MutableMapping):
            if linea.get("monto") is None:
                linea["monto"] = monto
        elif getattr(linea, "monto", None) is None:
            linea.monto = monto

    return totales
