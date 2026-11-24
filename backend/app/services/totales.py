"""Cálculo de totales de factura con Decimal y ROUND_HALF_UP.

Esquema oficial (app.models.facturacion):
- LineaFactura: cantidad, precio_unitario, descuento_pct, gravada, monto.
- Factura: subtotal, descuento_total, base_gravada, base_exenta, itbms,
  total y portes (Numeric(14, 2)).

Reglas aplicadas (pendientes de confirmar con el equipo, ver notas):
- El monto de cada línea se calcula y se redondea por línea:
      bruto    = cantidad * precio_unitario          (ROUND_HALF_UP a 2)
      descuento = bruto * descuento_pct / 100        (ROUND_HALF_UP a 2)
      monto    = bruto - descuento                   (ya con 2 decimales)
- subtotal       = suma de los montos netos de línea.
- descuento_total = suma de (bruto - monto) de cada línea; es informativo,
  ya está descontado dentro de subtotal.
- base_gravada   = suma de montos de líneas con gravada=True.
- base_exenta    = suma de montos de líneas con gravada=False.
- itbms          = base_gravada * 7% (ROUND_HALF_UP a 2). Solo líneas gravadas.
- total          = base_gravada + base_exenta + itbms + portes.

DUDAS ABIERTAS PARA EL EQUIPO:
1. Portes: se asume que NO generan ITBMS y se suman directo al total.
   Si el negocio grava portes, hay que mover portes a la base gravada.
2. precio_unitario vs precio_unidad / cobrar_por / unidades_por_caja:
   se asume que precio_unitario es el precio a cobrar por la cantidad
   indicada y que cobrar_por solo describe el empaque (no cambia el monto).
   Si "cobrar_por=caja" debe multiplicar por unidades_por_caja, avisar.
3. subtotal: se toma como el neto de descuentos por línea. Si el original
   muestra el bruto en "Subtotal" y el descuento aparte, cambiar el orden.

Las validaciones de cada línea (cantidad >= 0.01, precio_unitario >= 0,
descuento_pct entre 0 y 100) se delegan en app.utils.validators
(ruta oficial; app.services.Validators queda solo como re-export).
unidades_por_caja no se valida aquí: no afecta al monto y su default
lo aplica la base de datos.
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
TASA_ITBMS = Decimal("0.07")


def _a_centavos(valor: Decimal) -> Decimal:
    """Redondea a 2 decimales con ROUND_HALF_UP (regla del sistema)."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _campo(linea: Any, nombre: str, defecto: Any = None) -> Any:
    """Lee un campo de una línea que sea dict u objeto ORM."""
    if isinstance(linea, Mapping):
        return linea.get(nombre, defecto)
    return getattr(linea, nombre, defecto)


def _cantidad_precio(linea: Any) -> tuple[Decimal, Decimal]:
    """Valida cantidad y precio con las mismas reglas de Validators
    (cantidad >= 0.01, precio >= 0) y los devuelve como Decimal.
    No se valida unidades_por_caja aquí: no afecta al monto y su default
    lo pone la base de datos."""
    cantidad = validar_cantidad(_campo(linea, "cantidad"))
    precio = validar_precio(_campo(linea, "precio_unitario"))
    return cantidad, precio


def calcular_monto_linea(linea: Any) -> Decimal:
    """Devuelve el monto neto de una línea (cantidad x precio - descuento).

    Acepta LineaFactura (ORM) o dict con las mismas claves.
    Lanza ValueError si la línea no cumple las reglas del esquema.
    """
    cantidad, precio = _cantidad_precio(linea)
    descuento_raw = _campo(linea, "descuento_pct")
    descuento_pct = (
        Decimal("0") if descuento_raw is None else validar_descuento_pct(descuento_raw)
    )

    bruto = _a_centavos(cantidad * precio)
    descuento = _a_centavos(bruto * descuento_pct / Decimal("100"))
    return bruto - descuento


def calcular_bruto_linea(linea: Any) -> Decimal:
    """Devuelve cantidad x precio_unitario sin descontar, a 2 decimales."""
    cantidad, precio = _cantidad_precio(linea)
    return _a_centavos(cantidad * precio)


def calcular_totales(
    lineas: Iterable[Any], portes: Any = Decimal("0.00")
) -> dict[str, Decimal]:
    """Calcula los 6 campos de totales de Factura a partir de sus líneas.

    `portes` acepta Decimal, int, float o str numérico; None cuenta como 0.
    Devuelve dict con subtotal, descuento_total, base_gravada, base_exenta,
    itbms y total (todos Decimal con 2 decimales).
    """
    subtotal = Decimal("0.00")
    descuento_total = Decimal("0.00")
    base_gravada = Decimal("0.00")
    base_exenta = Decimal("0.00")

    for linea in lineas or []:
        bruto = calcular_bruto_linea(linea)
        monto = calcular_monto_linea(linea)

        subtotal += monto
        descuento_total += bruto - monto

        gravada = _campo(linea, "gravada", True)
        if gravada is None:
            gravada = True
        if gravada:
            base_gravada += monto
        else:
            base_exenta += monto

    itbms = _a_centavos(base_gravada * TASA_ITBMS)

    portes_dec = Decimal("0.00") if portes is None else a_decimal(portes, "portes")
    if portes_dec < 0:
        raise ValueError("portes no puede ser negativo")

    total = base_gravada + base_exenta + itbms + portes_dec

    return {
        "subtotal": _a_centavos(subtotal),
        "descuento_total": _a_centavos(descuento_total),
        "base_gravada": _a_centavos(base_gravada),
        "base_exenta": _a_centavos(base_exenta),
        "itbms": itbms,
        "total": _a_centavos(total),
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
