from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.facturacion import Categoria, Factura, LineaFactura, Producto


def test_factura_con_lineas():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)

    with Session(motor) as db:
        categoria = Categoria(nombre="Bebidas")
        producto = Producto(
            nombre="Agua 600 ml",
            sku="AGUA-600",
            categoria=categoria,
            precio_caja=Decimal("120.00"),
            precio_unidad=Decimal("10.00"),
            unidades_por_caja=12,
        )
        factura = Factura(
            numero_serie="FAC-2026-0001",
            codigo_verificacion="COD123",
            fecha=date(2026, 11, 23),
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
                    descripcion="Agua 600 ml",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("10.00"),
                    precio_unidad=Decimal("10.00"),
                    descuento_pct=Decimal("0.00"),
                    gravada=True,
                    unidades_por_caja=12,
                    monto=Decimal("10.70"),
                    producto=producto,
                )
            ],
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)

        assert factura.id is not None
        assert len(factura.lineas) == 1
        assert factura.lineas[0].factura_id == factura.id
        assert factura.lineas[0].producto_id == producto.id
