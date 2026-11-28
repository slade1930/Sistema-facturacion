"""Cálculo de métricas globales y por empresa para el panel admin. Etapa C1."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.catalogo import EstadoPedido, SectorEmpresa, TipoEmpaque
from app.models.inventario import TipoMovimiento
from app.repositories.metricas import MetricasRepository
from app.schemas.admin import (
    AuditoriaRead,
    CategoriaAdminRead,
    EmpresaDetalle,
    EmpresaResumen,
    IngresoEmpresa,
    IngresoGrupo,
    IngresoMes,
    IngresosDesglose,
    MovimientoInventarioRead,
    PanelResumen,
    PedidoAdminRead,
    ProductoAdminRead,
    ProductoRanking,
    ProductosRanking,
)
from app.schemas.catalogo import ProductoRead
from app.schemas.common import Pagina
from app.schemas.facturacion import FacturaResumen
from app.schemas.pedidos import PedidoB2BRead
from app.services.inventario import unidades_a_descontar

DIAS_POR_DEFECTO = 30
VENTANA_EN_LINEA = timedelta(minutes=15)
TOP = 10


def rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Rango inclusivo; por defecto, los últimos 30 días."""
    fin = hasta or date.today()
    inicio = desde or (fin - timedelta(days=DIAS_POR_DEFECTO))
    if inicio > fin:
        raise ValueError("La fecha 'desde' no puede ser posterior a 'hasta'.")
    return inicio, fin


def _d(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def _valor_enum(valor: Any, defecto: str) -> str:
    return str(getattr(valor, "value", valor) or defecto)


def resumen(db: Session, desde: date, hasta: date) -> PanelResumen:
    ahora = datetime.now(timezone.utc)
    datos = MetricasRepository(db).resumen(
        desde, hasta, ahora, VENTANA_EN_LINEA
    )
    return PanelResumen(
        generado_en=ahora, desde=desde, hasta=hasta, **datos
    )


def _meses(hasta: date) -> list[str]:
    """12 claves YYYY-MM consecutivas que terminan en el mes de 'hasta'."""
    claves = []
    anio, mes = hasta.year, hasta.month
    for _ in range(12):
        claves.append(f"{anio:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(claves))


def ingresos(db: Session, desde: date, hasta: date) -> IngresosDesglose:
    repo = MetricasRepository(db)
    primer_mes = _meses(hasta)[0]
    inicio_meses = date(int(primer_mes[:4]), int(primer_mes[5:7]), 1)
    mensuales = repo.ingresos_mensuales(hasta, inicio_meses)
    por_mes = [
        IngresoMes(
            mes=clave,
            ingresos=mensuales.get(clave, (Decimal("0.00"), 0))[0],
            facturas=mensuales.get(clave, (Decimal("0.00"), 0))[1],
        )
        for clave in _meses(hasta)
    ]

    por_empresa = []
    filas = repo.ingresos_por_empresa(desde, hasta)
    for empresa_id, nombre, total, conteo in filas[:TOP]:
        por_empresa.append(
            IngresoEmpresa(
                empresa_id=empresa_id,
                nombre=nombre,
                ingresos=total,
                facturas=conteo,
            )
        )
    if len(filas) > TOP:
        por_empresa.append(
            IngresoEmpresa(
                empresa_id=None,
                nombre="Otras",
                ingresos=sum((fila[2] for fila in filas[TOP:]), Decimal("0.00")),
                facturas=sum(fila[3] for fila in filas[TOP:]),
            )
        )

    por_sector = [
        IngresoGrupo(
            nombre=_valor_enum(sector, "sin_sector"),
            ingresos=total,
            facturas=conteo,
        )
        for sector, total, conteo in repo.ingresos_por_sector(desde, hasta)
    ]
    por_categoria = [
        IngresoGrupo(nombre=nombre, ingresos=total, facturas=conteo)
        for nombre, total, conteo in repo.ingresos_por_categoria(desde, hasta)
    ]
    return IngresosDesglose(
        desde=desde,
        hasta=hasta,
        por_mes=por_mes,
        por_empresa=por_empresa,
        por_sector=por_sector,
        por_categoria=por_categoria,
    )


def productos(
    db: Session,
    desde: date,
    hasta: date,
    cliente_id: int | None = None,
) -> ProductosRanking:
    """Rankings con una sola pasada por los agregados de pedidos del período."""
    acumulado: dict[int, dict[str, Any]] = {}
    for fila in MetricasRepository(db).ventas_productos(desde, hasta, cliente_id):
        (
            producto_id,
            nombre,
            sku,
            _categoria,
            _sector,
            tipo,
            unidades_por_caja,
            cantidad,
            monto,
            conteo,
        ) = fila
        item = acumulado.setdefault(
            int(producto_id),
            {
                "producto_id": int(producto_id),
                "nombre": nombre,
                "sku": sku,
                "unidades": Decimal("0.00"),
                "monto": Decimal("0.00"),
                "pedidos": 0,
            },
        )
        # La conversión es la misma del servicio de inventario; se aplica a
        # cada grupo (producto, presentación), no fila por fila.
        item["unidades"] += unidades_a_descontar(
            tipo or TipoEmpaque.UNIDAD,
            _d(cantidad),
            int(unidades_por_caja or 1),
        )
        item["monto"] += _d(monto)
        item["pedidos"] += int(conteo or 0)

    items = [ProductoRanking(**valor) for valor in acumulado.values()]
    return ProductosRanking(
        desde=desde,
        hasta=hasta,
        mas_pedidos_por_unidades=sorted(
            items, key=lambda item: (-item.unidades, item.nombre)
        )[:TOP],
        mas_pedidos_por_monto=sorted(
            items, key=lambda item: (-item.monto, item.nombre)
        )[:TOP],
        menos_pedidos=sorted(
            items, key=lambda item: (item.pedidos, item.unidades, item.nombre)
        )[:TOP],
    )


def _producto_admin(fila: Any) -> ProductoAdminRead:
    (
        producto,
        categoria_nombre,
        sector,
        existencias,
        stock_minimo,
        tipo,
        unidades_por_caja,
        cantidad,
        monto,
        pedidos,
    ) = fila
    datos = ProductoRead.model_validate(producto).model_dump()
    return ProductoAdminRead(
        **datos,
        categoria_nombre=categoria_nombre,
        sector=sector,
        existencias=_d(existencias),
        stock_minimo=_d(stock_minimo),
        ventas_unidades=unidades_a_descontar(
            tipo or TipoEmpaque.UNIDAD,
            _d(cantidad),
            int(unidades_por_caja or producto.unidades_por_caja or 1),
        ),
        ventas_monto=_d(monto),
        pedidos=int(pedidos or 0),
    )


def catalogo_productos(
    db: Session,
    desde: date,
    hasta: date,
    categoria_id: int | None,
    sector: SectorEmpresa | None,
    busqueda: str | None,
    solo_activos: bool,
    desplazamiento: int,
    limite: int,
) -> Pagina[ProductoAdminRead]:
    filas, total = MetricasRepository(db).catalogo_productos(
        desde,
        hasta,
        categoria_id,
        sector,
        busqueda,
        solo_activos,
        desplazamiento,
        limite,
    )
    return Pagina[ProductoAdminRead](
        items=[_producto_admin(fila) for fila in filas],
        total=total,
        limite=limite,
        desplazamiento=desplazamiento,
    )


def producto_admin(db: Session, producto_id: int, desde: date, hasta: date) -> ProductoAdminRead | None:
    filas, _ = MetricasRepository(db).catalogo_productos(
        desde,
        hasta,
        None,
        None,
        None,
        False,
        0,
        1,
        producto_id=producto_id,
    )
    return _producto_admin(filas[0]) if filas else None


def categorias_admin(
    db: Session,
    sector: SectorEmpresa | None,
    busqueda: str | None,
    desplazamiento: int,
    limite: int,
) -> Pagina[CategoriaAdminRead]:
    filas, total = MetricasRepository(db).categorias(
        sector, busqueda, desplazamiento, limite
    )
    return Pagina[CategoriaAdminRead](
        items=[
            CategoriaAdminRead(
                id=categoria.id,
                nombre=categoria.nombre,
                sector=categoria.sector,
                total_productos=int(conteo),
            )
            for categoria, conteo in filas
        ],
        total=total,
        limite=limite,
        desplazamiento=desplazamiento,
    )


def listar_empresas(
    db: Session,
    desde: date,
    hasta: date,
    sector: SectorEmpresa | None,
    activo: bool | None,
    busqueda: str | None,
    desplazamiento: int,
    limite: int,
) -> Pagina[EmpresaResumen]:
    filas, total = MetricasRepository(db).listar_empresas(
        desde, hasta, sector, activo, busqueda, desplazamiento, limite
    )
    items = []
    for cliente, cuenta_activa, comprado, ultima in filas:
        items.append(
            EmpresaResumen(
                id=cliente.id,
                nombre_empresa=cliente.nombre_empresa,
                ruc=cliente.ruc,
                sector=cliente.sector,
                activo=bool(cliente.activo),
                cuenta_activa=bool(cuenta_activa),
                total_comprado=_d(comprado),
                fecha_ultima_compra=ultima,
            )
        )
    return Pagina[EmpresaResumen](
        items=items, total=total, limite=limite, desplazamiento=desplazamiento
    )


def detalle_empresa(
    db: Session, cliente_id: int, desde: date, hasta: date
) -> EmpresaDetalle | None:
    repo = MetricasRepository(db)
    cliente, cuenta_activa, ingresos, ultima, pedidos, facturas = repo.obtener_empresa(
        cliente_id, desde, hasta
    )
    if cliente is None:
        return None
    return EmpresaDetalle(
        id=cliente.id,
        nombre_empresa=cliente.nombre_empresa,
        ruc=cliente.ruc,
        sector=cliente.sector,
        activo=bool(cliente.activo),
        cuenta_activa=cuenta_activa,
        direccion=cliente.direccion,
        telefono=cliente.telefono,
        email_contacto=cliente.email_contacto,
        sucursal=cliente.sucursal,
        fecha_registro=cliente.fecha_registro,
        total_comprado=ingresos,
        fecha_ultima_compra=ultima,
        ingresos=ingresos,
        pedidos_totales=pedidos,
        facturas_totales=facturas,
        productos_mas_comprados=productos(
            db, desde, hasta, cliente_id
        ).mas_pedidos_por_monto[:TOP],
        ultimas_facturas=[
            FacturaResumen.model_validate(factura)
            for factura in repo.ultimas_facturas(cliente_id)
        ],
        ultimos_pedidos=[
            PedidoB2BRead.model_validate(pedido)
            for pedido in repo.ultimos_pedidos(cliente_id)
        ],
    )


def listar_pedidos(
    db: Session,
    desde: date,
    hasta: date,
    estado: EstadoPedido | None,
    cliente_id: int | None,
    desplazamiento: int,
    limite: int,
) -> Pagina[PedidoAdminRead]:
    pedidos, total = MetricasRepository(db).listar_pedidos(
        desde, hasta, estado, cliente_id, desplazamiento, limite
    )
    items = []
    for pedido in pedidos:
        datos = PedidoB2BRead.model_validate(pedido).model_dump()
        items.append(
            PedidoAdminRead(
                **datos,
                nombre_empresa=(
                    pedido.cliente.nombre_empresa if pedido.cliente else None
                ),
            )
        )
    return Pagina[PedidoAdminRead](
        items=items, total=total, limite=limite, desplazamiento=desplazamiento
    )


def listar_movimientos(
    db: Session,
    producto_id: int | None,
    tipo: TipoMovimiento | None,
    desde: date,
    hasta: date,
    desplazamiento: int,
    limite: int,
) -> Pagina[MovimientoInventarioRead]:
    filas, total = MetricasRepository(db).movimientos(
        producto_id, tipo, desde, hasta, desplazamiento, limite
    )
    return Pagina[MovimientoInventarioRead](
        items=[MovimientoInventarioRead.model_validate(fila) for fila in filas],
        total=total,
        limite=limite,
        desplazamiento=desplazamiento,
    )


def listar_auditoria(
    db: Session,
    accion: str | None,
    cuenta_id: int | None,
    desde: date,
    hasta: date,
    desplazamiento: int,
    limite: int,
) -> Pagina[AuditoriaRead]:
    filas, total = MetricasRepository(db).auditoria(
        accion, cuenta_id, desde, hasta, desplazamiento, limite
    )
    return Pagina[AuditoriaRead](
        items=[AuditoriaRead.model_validate(fila) for fila in filas],
        total=total,
        limite=limite,
        desplazamiento=desplazamiento,
    )
