"""Gente: la duplicada debe calcar los montos ya guardados, no recalcularlos."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.facturacion import EstadoFactura, Factura, LineaFactura
from app.services import ciclo_vida
from app.services.totales import aplicar_totales

CAMPOS_TOTALES = (
    "subtotal",
    "descuento_total",
    "base_gravada",
    "base_exenta",
    "itbms",
    "total",
)


@pytest.fixture
def db():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def test_duplicar_conserva_montos_cuando_el_precio_tenia_mas_decimales(db, monkeypatch):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")
    monkeypatch.setattr(
        ciclo_vida,
        "siguiente_numero_factura",
        lambda _sesion, _anio: "FAC-2026-0002",
    )

    # Precio de entrada con 4 decimales: el monto se calcula con él, pero la
    # columna Numeric(14,2) guarda 1.01. Ahí estaba el desajuste al duplicar.
    original = Factura(
        numero_serie="FAC-2026-0001",
        codigo_verificacion="CODIGO0001",
        fecha=date(2026, 11, 27),
        cliente_nombre="Cliente QA",
        cliente_ruc="RUC-QA",
        lineas=[
            LineaFactura(
                orden=1,
                descripcion="Gravada con 3 decimales",
                cantidad=Decimal("3"),
                precio_unitario=Decimal("1.0066"),
                descuento_pct=Decimal("0"),
                gravada=True,
                monto=None,
            ),
            LineaFactura(
                orden=2,
                descripcion="Exenta",
                cantidad=Decimal("2"),
                precio_unitario=Decimal("5.00"),
                descuento_pct=Decimal("0"),
                gravada=False,
                monto=None,
            ),
            LineaFactura(
                orden=3,
                descripcion="Gravada con descuento",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("2.99"),
                descuento_pct=Decimal("5"),
                gravada=True,
                monto=None,
            ),
        ],
    )
    aplicar_totales(original)
    db.add(original)
    db.commit()
    db.refresh(original)

    # Escenario exacto que se rompía: precio ya redondeado, monto no.
    assert original.lineas[0].precio_unitario == Decimal("1.01")
    assert original.lineas[0].monto == Decimal("3.02")

    duplicada = ciclo_vida.duplicar_factura(db, original, fecha=date(2026, 11, 27))
    db.flush()

    for campo in CAMPOS_TOTALES:
        assert getattr(duplicada, campo) == getattr(original, campo), campo

    montos_originales = [(l.orden, l.precio_unitario, l.monto) for l in original.lineas]
    montos_duplicados = [(l.orden, l.precio_unitario, l.monto) for l in duplicada.lineas]
    assert montos_duplicados == montos_originales

    assert duplicada.numero_serie == "FAC-2026-0002"
    assert duplicada.numero_serie != original.numero_serie
    assert duplicada.codigo_verificacion != original.codigo_verificacion
    assert duplicada.estado is EstadoFactura.EMITIDA
    assert duplicada.fecha_anulacion is None
    assert duplicada.puntaje_anomalia is None
    assert duplicada.motivo_anomalia is None

    # La original no se toca.
    assert original.numero_serie == "FAC-2026-0001"
    assert original.total == Decimal("16.27")
