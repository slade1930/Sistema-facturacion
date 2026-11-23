from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.facturacion import Factura, LineaFactura


def test_factura_con_lineas():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)

    with Session(motor) as db:
        factura = Factura(
            numero_factura="FAC-2026-0001",
            negocio_razon_social="Mi negocio",
            negocio_ruc="123456789",
            cliente_nombre="Cliente de prueba",
            codigo_verificacion="CODIGO123",
            lineas=[
                LineaFactura(
                    numero_linea=1,
                    descripcion="Servicio de prueba",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("10.00"),
                    tasa_itbms=Decimal("7.00"),
                    base_imponible=Decimal("10.00"),
                    impuesto=Decimal("0.70"),
                    total_linea=Decimal("10.70"),
                )
            ],
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)

        assert factura.id is not None
        assert len(factura.lineas) == 1
        assert factura.lineas[0].factura_id == factura.id