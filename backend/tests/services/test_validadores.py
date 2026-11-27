"""Pruebas de los validadores.

La fuente oficial es app.utils.validators; todos los imports deben
apuntar ahí directamente (ya no existe el shim app.services.Validators).
"""

from decimal import Decimal

import app.utils.validators as oficial
from app.utils import validators as oficial_directo


def test_todas_las_rutas_exponen_las_mismas_funciones():
    assert oficial_directo is oficial
    nombres = oficial.__all__
    assert nombres, "utils.validators debe declarar __all__"
    for nombre in nombres:
        assert hasattr(oficial, nombre), nombre
        assert getattr(oficial, nombre) is getattr(oficial_directo, nombre), nombre


def test_comportamiento_validar_cantidad_se_conserva():
    assert oficial.validar_cantidad(Decimal("2.5")) == Decimal("2.5")
    for malo in (None, Decimal("0"), Decimal("0.001"), "abc"):
        try:
            oficial.validar_cantidad(malo)
        except ValueError:
            pass
        else:
            raise AssertionError(f"validar_cantidad aceptó {malo!r}")


def test_series_validas():
    assert oficial.es_serie_factura_valida("FAC-2026-0001")
    assert oficial.es_serie_oc_valida("OC-2026-0042")
    assert not oficial.es_serie_factura_valida("OC-2026-0042")
    assert oficial.extraer_anio("FAC-2026-0001") == 2026


def test_totales_importa_desde_la_ruta_oficial():
    # Si alguien revierte totales.py al shim, este test lo detecta.
    import app.services.totales as totales

    assert totales.a_decimal is oficial.a_decimal
    assert totales.validar_cantidad is oficial.validar_cantidad
    assert totales.validar_precio is oficial.validar_precio
    assert totales.validar_descuento_pct is oficial.validar_descuento_pct
