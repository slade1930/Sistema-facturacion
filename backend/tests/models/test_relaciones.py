from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Categoria,
    ClienteB2B,
    Factura,
    LineaFactura,
    PedidoB2B,
    Producto,
)


def _factura_de_prueba(lineas=None):
    return Factura(
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
        lineas=lineas or [],
    )


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
        factura = _factura_de_prueba(
            [
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
            ]
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)

        assert factura.id is not None
        assert len(factura.lineas) == 1
        assert factura.lineas[0].factura_id == factura.id
        assert factura.lineas[0].producto_id == producto.id


def test_default_gravada_true_y_enum_defaults():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)

    with Session(motor) as db:
        factura = _factura_de_prueba(
            [
                LineaFactura(
                    orden=1,
                    descripcion="Sin gravada explícita",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("10.00"),
                    monto=Decimal("10.00"),
                )
            ]
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)

        linea = factura.lineas[0]
        assert linea.gravada is True
        assert linea.unidades_por_caja == 1
        assert linea.cobrar_por.value == "unidad"
        assert factura.condicion_pago.value == "contado"
        assert factura.estado.value == "emitida"
        assert factura.mostrar_ruc is True


def test_relacion_factura_a_pedidos_en_los_dos_sentidos():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)

    with Session(motor) as db:
        factura = _factura_de_prueba()
        cliente = ClienteB2B(
            nombre_empresa="Cliente B2B",
            ruc="1-234-567",
            email_contacto="contacto@example.com",
        )
        pedido = PedidoB2B(cliente=cliente, factura_generada=factura)
        db.add(pedido)
        db.commit()
        db.refresh(factura)
        db.refresh(pedido)

        assert pedido.factura_generada_id == factura.id
        assert pedido.factura_generada is factura
        assert [p.id for p in factura.pedido_origen] == [pedido.id]
        assert pedido.estado.value == "pendiente"
