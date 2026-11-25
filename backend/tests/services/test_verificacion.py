from decimal import Decimal

import pytest

from app.services.verificacion import (
    generar_codigo_verificacion,
    validar_codigo_verificacion,
)


def test_codigo_hmac_es_estable_y_total_se_normaliza(monkeypatch):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")

    codigo = generar_codigo_verificacion(
        "FAC-2026-0001", Decimal("10.00"), "123456789"
    )

    assert len(codigo) == 12
    assert all(caracter in "0123456789ABCDEF" for caracter in codigo)
    assert codigo == generar_codigo_verificacion(
        "FAC-2026-0001", Decimal("10"), "123456789"
    )


def test_validar_codigo_detecta_datos_o_codigo_incorrectos(monkeypatch):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")
    codigo = generar_codigo_verificacion(
        "FAC-2026-0001", Decimal("10.00"), "123456789"
    )

    assert validar_codigo_verificacion(
        codigo, "FAC-2026-0001", Decimal("10.00"), "123456789"
    )
    assert not validar_codigo_verificacion(
        codigo, "FAC-2026-0001", Decimal("11.00"), "123456789"
    )
    assert not validar_codigo_verificacion(
        "código-inválido", "FAC-2026-0001", Decimal("10.00"), "123456789"
    )


def test_generar_codigo_falla_si_no_hay_clave(monkeypatch):
    monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)

    with pytest.raises(RuntimeError, match="FACTURA_HMAC_KEY"):
        generar_codigo_verificacion("FAC-2026-0001", Decimal("10.00"))


@pytest.mark.parametrize("total", ["NaN", "infinity", "no-numérico"])
def test_generar_codigo_rechaza_totales_invalidos(monkeypatch, total):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")

    with pytest.raises(ValueError):
        generar_codigo_verificacion("FAC-2026-0001", total)
