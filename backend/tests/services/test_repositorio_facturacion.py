from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - registra todos los modelos en Base.metadata
from app.db.base import Base
from app.models.facturacion import EstadoFactura, Factura, LineaFactura
from app.repositories.facturacion import (
    ConfiguracionNegocioRepository,
    ContadorSerieRepository,
    FacturaRepository,
)
from app.schemas.facturacion import (
    ConfiguracionNegocioBase,
    ConfiguracionNegocioUpdate,
)
from app.services.ciclo_vida import FacturaYaAnuladaError
from app.services.verificacion import generar_codigo_verificacion


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _crear_factura_ejemplo(
    db_session,
    *,
    numero_serie: str = "FAC-2026-0001",
    codigo_verificacion: str = "ABCDEF123456",
) -> Factura:
    factura = Factura(
        numero_serie=numero_serie,
        codigo_verificacion=codigo_verificacion,
        fecha=date(2026, 11, 25),
        cliente_nombre="Cliente Prueba S.A.",
        cliente_ruc="8-888-888",
        subtotal=Decimal("100.00"),
        descuento_total=Decimal("0.00"),
        base_gravada=Decimal("100.00"),
        base_exenta=Decimal("0.00"),
        itbms=Decimal("7.00"),
        total=Decimal("107.00"),
    )
    linea = LineaFactura(
        orden=1,
        descripcion="Producto de prueba",
        cantidad=Decimal("1.00"),
        precio_unitario=Decimal("100.00"),
        monto=Decimal("100.00"),
    )
    return FacturaRepository.crear(db_session, factura, [linea])


def test_anular_factura_y_rechazar_doble_anulacion(db_session):
    factura = _crear_factura_ejemplo(db_session)

    anulada = FacturaRepository.anular(db_session, factura)
    assert anulada.estado == EstadoFactura.ANULADA
    assert anulada.fecha_anulacion is not None

    with pytest.raises(FacturaYaAnuladaError):
        FacturaRepository.anular(db_session, anulada)


def test_verificar_codigo_hmac(db_session, monkeypatch):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-secreta-pruebas")
    codigo = generar_codigo_verificacion(
        "FAC-2026-0002", Decimal("107.00"), "8-888-888"
    )
    _crear_factura_ejemplo(
        db_session,
        numero_serie="FAC-2026-0002",
        codigo_verificacion=codigo,
    )

    encontrada = FacturaRepository.verificar(db_session, "FAC-2026-0002", codigo)
    assert encontrada is not None
    assert encontrada.numero_serie == "FAC-2026-0002"

    assert (
        FacturaRepository.verificar(db_session, "FAC-2026-0002", "000000000000")
        is None
    )
    assert FacturaRepository.verificar(db_session, "FAC-2026-9999", codigo) is None


def test_configuracion_negocio_actualizacion_parcial(db_session):
    inicial = ConfiguracionNegocioRepository.guardar_o_actualizar(
        db_session,
        ConfiguracionNegocioBase(
            empresa_nombre="Distribuidora PTY",
            empresa_ruc="12345-1-67890",
        ),
    )
    assert inicial.empresa_nombre == "Distribuidora PTY"

    actualizada = ConfiguracionNegocioRepository.guardar_o_actualizar(
        db_session,
        ConfiguracionNegocioUpdate(empresa_telefono="6000-0000"),
    )
    assert actualizada.empresa_telefono == "6000-0000"
    assert actualizada.empresa_nombre == "Distribuidora PTY"
    assert actualizada.empresa_ruc == "12345-1-67890"


def test_contador_serie_delega_en_servicio(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.repositories.facturacion.siguiente_numero_factura",
        lambda db, anio: f"FAC-{anio}-0001",
    )

    numero = ContadorSerieRepository.obtener_siguiente_numero(db_session, 2026)
    assert numero == "FAC-2026-0001"
