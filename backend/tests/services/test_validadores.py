"""Pruebas de la unificación de validadores.

La fuente oficial es app.utils.validators; app.services.Validators debe
seguir funcionando como re-export para no romper imports viejos.
"""

from decimal import Decimal

import app.services.Validators as shim
import app.utils.validators as oficial
from app.utils import validators as oficial_directo


def test_ambas_rutas_exponen_las_mismas_funciones():
    nombres = oficial.__all__
    assert nombres, "utils.validators debe declarar __all__"
    for nombre in nombres:
        assert getattr(oficial, nombre) is getattr(shim, nombre), nombre
        assert getattr(oficial_directo, nombre) is getattr(shim, nombre), nombre


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
