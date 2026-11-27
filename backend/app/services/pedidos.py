"""CÃ¡lculos y ciclo de facturaciÃ³n de pedidos B2B."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.catalogo import (
    EstadoPedido,
    TipoEmpaque,
    PedidoB2B,
    LineaPedidoB2B,
    Producto,
)
from app.models.facturacion import (
    CobrarPor,
    Factura,
    LineaFactura,
)
from app.repositories.facturacion import (
    FacturaRepository,
    ContadorSerieRepository,
)
from app.services.totales import calcular_totales, aplicar_totales
from app.services.verificacion import generar_codigo_verificacion


CENTAVOS = Decimal("0.01")



def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def precio_unitario(
    precios: dict[TipoEmpaque, Decimal],
    presentacion: TipoEmpaque,
) -> Decimal:
    if presentacion not in precios:
        raise ValueError(f"No hay precio para {presentacion.value}")
    return precios[presentacion]


def subtotal_linea(precio: Decimal, cantidad: int | Decimal) -> Decimal:
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")
    return redondear(precio * cantidad)


def subtotal_pedido(subtotales_lineas: list[Decimal]) -> Decimal:
    return redondear(sum(subtotales_lineas, Decimal("0")))


@dataclass(frozen=True)
class LineaPedido:
    descripcion: str
    presentacion: TipoEmpaque
    cantidad: int | Decimal
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
        raise ValueError("El pedido no tiene lÃ­neas")
    subtotales = [linea.subtotal for linea in lineas]
    return ResumenPedido(subtotales, subtotal_pedido(subtotales))


@dataclass(frozen=True)
class LineaFacturaBorrador:
    """Misma forma bÃ¡sica que LineaFacturaCreate."""

    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    precio_unidad: Decimal | None
    descuento_pct: Decimal
    gravada: bool
    unidades_por_caja: int
    cobrar_por: str
    producto_id: int | None


def pedido_a_lineas_factura(
    lineas: list[LineaPedido],
) -> list[LineaFacturaBorrador]:
    if not lineas:
        raise ValueError("El pedido no tiene lÃ­neas")

    resultado = []

    for linea in lineas:
        es_media_caja = linea.presentacion == TipoEmpaque.MEDIA_CAJA
        es_caja = linea.presentacion == TipoEmpaque.CAJA

        resultado.append(
            LineaFacturaBorrador(
                descripcion=(
                    f"Media caja - {linea.descripcion}"
                    if es_media_caja
                    else linea.descripcion
                ),
                cantidad=Decimal(linea.cantidad),
                precio_unitario=linea.precio,
                precio_unidad=(
                    None
                    if es_media_caja or es_caja
                    else linea.precio_unidad
                ),
                descuento_pct=linea.descuento_pct,
                gravada=linea.gravada,
                unidades_por_caja=linea.unidades_por_caja,
                cobrar_por=(
                    CobrarPor.UNIDAD.value
                    if es_media_caja
                    else linea.presentacion.value
                ),
                producto_id=linea.producto_id,
            )
        )

    return resultado


def precio_de_presentacion(
    producto,
    presentacion: TipoEmpaque,
) -> Decimal:
    """Obtiene el precio segÃºn la presentaciÃ³n seleccionada."""

    if presentacion == TipoEmpaque.CAJA:
        return producto.precio_caja

    if presentacion == TipoEmpaque.UNIDAD:
        return producto.precio_unidad

    if not producto.permite_media_caja or producto.precio_media_caja is None:
        raise ValueError(
            f"'{producto.nombre}' no se vende por media caja"
        )

    return producto.precio_media_caja


def linea_pedido_desde_modelo(
    linea_modelo,
    producto,
) -> LineaPedido:
    """Convierte una lÃ­nea de pedido y su producto en una LineaPedido."""

    valor = getattr(
        linea_modelo.tipo_empaque,
        "value",
        linea_modelo.tipo_empaque,
    )
    presentacion = TipoEmpaque(valor)

    es_media_caja = presentacion == TipoEmpaque.MEDIA_CAJA
    es_caja = presentacion == TipoEmpaque.CAJA

    return LineaPedido(
        descripcion=producto.nombre,
        presentacion=presentacion,
        cantidad=linea_modelo.cantidad,
        precio=precio_de_presentacion(producto, presentacion),
        unidades_por_caja=producto.unidades_por_caja,
        precio_unidad=(
            None
            if es_media_caja or es_caja
            else producto.precio_unidad
        ),
        gravada=producto.aplica_itbms,
        producto_id=producto.id,
    )


def validar_pedido_facturable(
    estado,
    factura_generada_id: int | None,
) -> None:
    """Falla si el pedido ya fue facturado o estÃ¡ cancelado."""

    valor = getattr(estado, "value", estado)

    if factura_generada_id is not None or valor == EstadoPedido.FACTURADO.value:
        raise ValueError("El pedido ya fue facturado")

    if valor == EstadoPedido.CANCELADO.value:
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
    """Copia los datos del cliente B2B a los campos de la factura."""

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
    """Arma los campos de Factura a partir del pedido calculado."""

    faltan = [campo for campo in CAMPOS_TOTALES if campo not in totales]

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
    datos.update({campo: totales[campo] for campo in CAMPOS_TOTALES})

    return datos


def facturar_pedido_b2b(
    db: Session,
    pedido_id: int,
) -> Factura:
    """Genera una factura a partir de un pedido B2B.

    No realiza commit. La transacciÃ³n queda bajo el control del llamador.
    """

    pedido = db.scalar(
        select(PedidoB2B)
        .where(PedidoB2B.id == pedido_id)
        .with_for_update()
    )

    if pedido is None:
        raise ValueError(
            f"No existe el pedido B2B con ID {pedido_id}"
        )

    validar_pedido_facturable(
        pedido.estado,
        pedido.factura_generada_id,
    )

    # Cargar las relaciones necesarias despuÃ©s de bloquear el pedido.
    pedido = db.scalar(
        select(PedidoB2B)
        .options(
            joinedload(PedidoB2B.cliente),
            selectinload(PedidoB2B.lineas)
            .joinedload(LineaPedidoB2B.producto)
            .joinedload(Producto.categoria),
        )
        .where(PedidoB2B.id == pedido_id)
    )

    if pedido is None:
        raise ValueError(
            f"No existe el pedido B2B con ID {pedido_id}"
        )

    validar_pedido_facturable(
        pedido.estado,
        pedido.factura_generada_id,
    )

    if pedido.cliente is None:
        raise ValueError("El pedido no tiene un cliente asociado")

    if not pedido.lineas:
        raise ValueError("El pedido no tiene lÃ­neas para facturar")

    lineas_factura = []

    for linea_modelo in pedido.lineas:
        producto = linea_modelo.producto

        if producto is None:
            raise ValueError(
                f"La lÃ­nea {linea_modelo.id} no tiene un producto asociado"
            )

        linea_convertida = linea_pedido_desde_modelo(
            linea_modelo,
            producto,
        )

        es_media_caja = (
            linea_convertida.presentacion == TipoEmpaque.MEDIA_CAJA
        )

        es_caja = (
            linea_convertida.presentacion == TipoEmpaque.CAJA
        )
            # MEDIA_CAJA se registra como UNIDAD porque CobrarPor
            # solo admite CAJA o UNIDAD. Se conserva la cantidad de
            # medias cajas y se utiliza precio_media_caja como precio.
        cobrar_por = (
            CobrarPor.CAJA
            if es_caja
            else CobrarPor.UNIDAD
        )

        categoria = (
            producto.categoria.nombre
            if producto.categoria is not None
            else None
        )

        linea_factura = LineaFactura(
            orden=linea_modelo.orden,
            descripcion=(
                f"Media caja - {producto.nombre}"
                if es_media_caja
                else producto.nombre
            ),
            codigo_barras=producto.codigo_barras,
            categoria=categoria,
            cantidad=Decimal(linea_modelo.cantidad),
            precio_unitario=linea_convertida.precio,
            precio_unidad=(
                None
                if es_media_caja or es_caja
                else linea_convertida.precio_unidad
            ),
            descuento_pct=Decimal("0.00"),
            gravada=linea_convertida.gravada,
            unidades_por_caja=linea_convertida.unidades_por_caja,
            cobrar_por=cobrar_por,
            monto=None,
            producto_id=producto.id,
        )

        lineas_factura.append(linea_factura)

    fecha = date.today()
    portes = Decimal("0.00")

    numero_serie = ContadorSerieRepository.obtener_siguiente_numero(
        db,
        fecha.year,
    )

    totales = calcular_totales(
        lineas_factura,
        portes=portes,
    )

    codigo_verificacion = generar_codigo_verificacion(
        numero_serie,
        totales["total"],
        pedido.cliente.ruc or "",
    )

    datos_factura = armar_datos_factura(
        cliente=pedido.cliente,
        totales=totales,
        numero_serie=numero_serie,
        codigo_verificacion=codigo_verificacion,
        fecha=fecha,
        notas=pedido.notas,
        portes=portes,
    )

    factura = Factura(**datos_factura)

    # Asignar las lÃ­neas antes de aplicar los totales.
    factura.lineas = lineas_factura
    aplicar_totales(factura)

    # Se guarda con flush, sin confirmar la transacciÃ³n.
    FacturaRepository.crear(
        db,
        factura,
        lineas_factura,
        commit=False,
    )

    pedido.factura_generada_id = factura.id
    pedido.estado = EstadoPedido.FACTURADO

    db.flush()

    return factura
