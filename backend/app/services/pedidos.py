"""Cálculos de pedidos B2B: precios por presentación y subtotales."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

CENTAVOS = Decimal("0.01")


class Presentacion(str, Enum):
    CAJA = "caja"
    MEDIA_CAJA = "media_caja"
    UNIDAD = "unidad"


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def precio_unitario(
    precios: dict[Presentacion, Decimal], presentacion: Presentacion
) -> Decimal:
    if presentacion not in precios:
        raise ValueError(f"No hay precio para {presentacion.value}")
    return precios[presentacion]


def subtotal_linea(precio: Decimal, cantidad: int) -> Decimal:
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")
    return redondear(precio * cantidad)


def subtotal_pedido(subtotales_lineas: list[Decimal]) -> Decimal:
    return redondear(sum(subtotales_lineas, Decimal("0")))


@dataclass(frozen=True)
class LineaPedido:
    descripcion: str
    presentacion: Presentacion
    cantidad: int
    precio: Decimal
    unidades_por_caja: int = 1
    precio_unidad: Decimal | None = None
    descuento_pct: Decimal = Decimal("0.00")
    gravada: bool = True
    producto_id: int | None = None

    def __post_init__(self):
        if not isinstance(self.precio, Decimal):
            raise TypeError("El precio debe ser Decimal")
        if self.precio < 0:
            raise ValueError("El precio no puede ser negativo")
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        if self.unidades_por_caja < 1:
            raise ValueError("unidades_por_caja debe ser al menos 1")
        if not Decimal("0") <= self.descuento_pct <= Decimal("100"):
            raise ValueError("El descuento debe estar entre 0 y 100")

    @property
    def subtotal(self) -> Decimal:
        return subtotal_linea(self.precio, self.cantidad)


@dataclass(frozen=True)
class ResumenPedido:
    subtotales_lineas: list[Decimal]
    subtotal: Decimal


def calcular_pedido(lineas: list[LineaPedido]) -> ResumenPedido:
    if not lineas:
        raise ValueError("El pedido no tiene líneas")
    subtotales = [l.subtotal for l in lineas]
    return ResumenPedido(subtotales, subtotal_pedido(subtotales))


@dataclass(frozen=True)
class LineaFacturaBorrador:
    """Misma forma que LineaFacturaCreate (schemas/facturacion.py)."""
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    precio_unidad: Decimal | None
    descuento_pct: Decimal
    gravada: bool
    unidades_por_caja: int
    cobrar_por: str
    producto_id: int | None


def pedido_a_lineas_factura(lineas: list[LineaPedido]) -> list[LineaFacturaBorrador]:
    if not lineas:
        raise ValueError("El pedido no tiene líneas")
    resultado = []
    for l in lineas:
        if l.presentacion == Presentacion.MEDIA_CAJA:
            # TODO: definir con Erick y el equipo 2 cómo se factura la media caja
            raise NotImplementedError("Media caja: pendiente de definir")
        resultado.append(
            LineaFacturaBorrador(
                descripcion=l.descripcion,
                cantidad=Decimal(l.cantidad),
                precio_unitario=l.precio,
                precio_unidad=l.precio_unidad,
                descuento_pct=l.descuento_pct,
                gravada=l.gravada,
                unidades_por_caja=l.unidades_por_caja,
                cobrar_por=l.presentacion.value,
                producto_id=l.producto_id,
            )
        )
    return resultado


def validar_pedido_facturable(estado, factura_generada_id: int | None) -> None:
    """Falla si el pedido ya fue facturado o está cancelado.

    `estado` acepta el enum EstadoPedido o su texto ("pendiente", ...).
    """
    valor = getattr(estado, "value", estado)
    if factura_generada_id is not None or valor == "facturado":
        raise ValueError("El pedido ya fue facturado")
    if valor == "cancelado":
        raise ValueError("Un pedido cancelado no se puede facturar")


CAMPOS_TOTALES = (
    "subtotal",
    "descuento_total",
    "base_gravada",
    "base_exenta",
    "itbms",
    "total",
)


def datos_cliente_para_factura(cliente) -> dict:
    """Copia los datos de un ClienteB2B a los campos cliente_* de Factura."""
    direccion = cliente.direccion
    return {
        "cliente_nombre": cliente.nombre_empresa,
        "cliente_ruc": cliente.ruc,
        "cliente_direccion": direccion[:250] if direccion else None,
        "cliente_telefono": cliente.telefono,
        "cliente_correo": cliente.email_contacto,
    }


def armar_datos_factura(
    cliente,
    totales: dict,
    numero_serie: str,
    codigo_verificacion: str,
    fecha: date,
    orden_compra: str | None = None,
    notas: str | None = None,
    portes: Decimal = Decimal("0.00"),
) -> dict:
    """Arma los campos de Factura a partir del pedido ya calculado."""
    faltan = [c for c in CAMPOS_TOTALES if c not in totales]
    if faltan:
        raise ValueError(f"Faltan totales: {', '.join(faltan)}")
    if len(numero_serie) > 20:
        raise ValueError("numero_serie excede 20 caracteres")
    if len(codigo_verificacion) > 12:
        raise ValueError("codigo_verificacion excede 12 caracteres")

    datos = {
        "numero_serie": numero_serie,
        "codigo_verificacion": codigo_verificacion,
        "fecha": fecha,
        "orden_compra": orden_compra,
        "notas": notas,
        "portes": portes,
    }
    datos.update(datos_cliente_para_factura(cliente))
    datos.update({c: totales[c] for c in CAMPOS_TOTALES})
    return datos


# TODO (coordinar con equipo 2): totales con ITBMS (totales.py), numeración
#  FAC/OC (serie.py) y código de verificación HMAC; guardar con
#  FacturaRepository.crear(db, factura, lineas, commit=False).