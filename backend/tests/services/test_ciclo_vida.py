from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.facturacion import EstadoFactura, Factura, LineaFactura
from app.services import ciclo_vida
from app.services.ciclo_vida import (
    FacturaYaAnuladaError,
    anular_factura,
    duplicar_factura,
)


def _crear_factura() -> Factura:
    return Factura(
        numero_serie="FAC-2026-0001",
        codigo_verificacion="ORIGINAL123",
        fecha=date(2026, 11, 24),
        cliente_nombre="Cliente de prueba",
        cliente_ruc="123456789",
        subtotal=Decimal("10.00"),
        descuento_total=Decimal("0.00"),
        base_gravada=Decimal("10.00"),
        base_exenta=Decimal("0.00"),
        itbms=Decimal("0.70"),
        total=Decimal("10.70"),
        lineas=[
            LineaFactura(
                orden=1,
                descripcion="Producto de prueba",
                cantidad=Decimal("1.00"),
                precio_unitario=Decimal("10.00"),
                descuento_pct=Decimal("0.00"),
                gravada=True,
                monto=Decimal("10.00"),
            )
        ],
    )


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_anular_conserva_factura_folio_y_fecha_de_anulacion(db):
    factura = _crear_factura()
    db.add(factura)
    db.commit()
    factura_id = factura.id
    fecha_anulacion = datetime(2026, 11, 24, 17, 30, tzinfo=timezone.utc)

    resultado = anular_factura(factura, ahora=fecha_anulacion)
    db.flush()

    assert resultado is factura
    assert factura.estado is EstadoFactura.ANULADA
    assert factura.fecha_anulacion == fecha_anulacion
    assert factura.numero_serie == "FAC-2026-0001"
    assert db.get(Factura, factura_id) is factura
    assert db.scalar(select(func.count()).select_from(Factura)) == 1


def test_anular_asigna_fecha_utc_si_no_se_proporciona():
    factura = _crear_factura()

    anular_factura(factura)

    assert factura.fecha_anulacion is not None
    assert factura.fecha_anulacion.utcoffset() == timedelta(0)


def test_no_reanula_ni_reemplaza_fecha_de_trazabilidad():
    factura = _crear_factura()
    factura.estado = EstadoFactura.ANULADA
    fecha_original = datetime(2026, 11, 24, 16, 0, tzinfo=timezone.utc)
    factura.fecha_anulacion = fecha_original

    with pytest.raises(FacturaYaAnuladaError):
        anular_factura(factura)

    assert factura.fecha_anulacion == fecha_original


def test_duplicar_asigna_nuevo_folio_codigo_y_no_modifica_original(
    db, monkeypatch
):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")
    factura = _crear_factura()
    db.add(factura)
    db.commit()
    factura_id = factura.id
    folios_solicitados = []

    def siguiente_folio(_session, anio):
        folios_solicitados.append(anio)
        return "FAC-2027-0001"

    monkeypatch.setattr(ciclo_vida, "siguiente_numero_factura", siguiente_folio)

    duplicada = duplicar_factura(db, factura, fecha=date(2027, 1, 2))

    assert folios_solicitados == [2027]
    assert duplicada.id != factura_id
    assert duplicada.numero_serie == "FAC-2027-0001"
    assert duplicada.numero_serie != factura.numero_serie
    assert duplicada.codigo_verificacion != factura.codigo_verificacion
    assert duplicada.estado is EstadoFactura.EMITIDA
    assert duplicada.fecha_anulacion is None
    assert duplicada.fecha == date(2027, 1, 2)
    assert duplicada.total == Decimal("10.70")
    assert duplicada.lineas[0].orden == 1
    assert duplicada.lineas[0].monto == Decimal("10.00")
    assert factura.numero_serie == "FAC-2026-0001"
    assert factura.codigo_verificacion == "ORIGINAL123"
    assert factura.estado is EstadoFactura.EMITIDA
    assert db.scalar(select(func.count()).select_from(Factura)) == 2
