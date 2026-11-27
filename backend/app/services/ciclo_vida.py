"""Reglas de ciclo de vida de facturas."""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.facturacion import EstadoFactura, Factura, LineaFactura
from app.services.serie import siguiente_numero_factura
from app.services.verificacion import generar_codigo_verificacion


class FacturaYaAnuladaError(ValueError):
    """Se intentó anular una factura que ya estaba anulada."""


def anular_factura(
    factura: Factura, ahora: datetime | None = None
) -> Factura:
    """Anula la factura sin borrarla ni modificar su número de serie."""
    # Impide anular dos veces y conserva la fecha original de trazabilidad.
    if factura.estado == EstadoFactura.ANULADA:
        raise FacturaYaAnuladaError(
            f"La factura {factura.numero_serie} ya está anulada."
        )

    # Cambia solo el estado y registra cuándo se produjo la anulación.
    factura.estado = EstadoFactura.ANULADA
    factura.fecha_anulacion = (
        ahora if ahora is not None else datetime.now(timezone.utc)
    )
    return factura


def duplicar_factura(
    db: Session, factura: Factura, fecha: date | None = None
) -> Factura:
    """Crea y agrega a la sesión una factura nueva basada en la original.

    No hace commit; la transacción queda a cargo del endpoint o servicio
    coordinador que invoque esta función.
    """
    # Usa la fecha indicada o la fecha actual para determinar el nuevo folio.
    fecha_nueva = fecha if fecha is not None else datetime.now(timezone.utc).date()
    numero_serie = siguiente_numero_factura(db, fecha_nueva.year)

    # Copia las líneas en orden y respeta los montos ya guardados. Recalcular
    # desde precio_unitario (redondeado a 2 decimales en la BD) cambiaría el total.
    lineas = [
        LineaFactura(
            orden=orden,
            descripcion=linea.descripcion,
            codigo_barras=linea.codigo_barras,
            categoria=linea.categoria,
            cantidad=linea.cantidad,
            precio_unitario=linea.precio_unitario,
            precio_unidad=linea.precio_unidad,
            descuento_pct=linea.descuento_pct,
            gravada=linea.gravada,
            unidades_por_caja=linea.unidades_por_caja,
            cobrar_por=linea.cobrar_por,
            monto=linea.monto,
            producto_id=linea.producto_id,
        )
        for orden, linea in enumerate(
            sorted(factura.lineas, key=lambda item: item.orden), start=1
        )
    ]

    # Crea una factura emitida nueva con los datos fiscales y comerciales originales.
    nueva = Factura(
        numero_serie=numero_serie,
        codigo_verificacion="",
        fecha=fecha_nueva,
        cliente_nombre=factura.cliente_nombre,
        cliente_ruc=factura.cliente_ruc,
        mostrar_ruc=factura.mostrar_ruc,
        cliente_direccion=factura.cliente_direccion,
        cliente_telefono=factura.cliente_telefono,
        cliente_correo=factura.cliente_correo,
        sucursal=factura.sucursal,
        vendedor=factura.vendedor,
        orden_compra=factura.orden_compra,
        condicion_pago=factura.condicion_pago,
        portes=factura.portes,
        notas=factura.notas,
        estado=EstadoFactura.EMITIDA,
        fecha_anulacion=None,
        lineas=lineas,
    )
    # Copia los totales de la original y genera un código para el nuevo folio.
    for campo in (
        "subtotal",
        "descuento_total",
        "base_gravada",
        "base_exenta",
        "itbms",
        "total",
    ):
        setattr(nueva, campo, getattr(factura, campo))

    nueva.codigo_verificacion = generar_codigo_verificacion(
        nueva.numero_serie,
        nueva.total,
        nueva.cliente_ruc or "",
    )

    db.add(nueva)
    db.flush()
    return nueva
