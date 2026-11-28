"""Consultas agregadas del panel y la administración. Rol admin; etapa C1."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalogo import (
    Categoria,
    ClienteB2B,
    EstadoPedido,
    LineaPedidoB2B,
    PedidoB2B,
    Producto,
    SectorEmpresa,
    TipoEmpaque,
)
from app.models.facturacion import EstadoFactura, Factura, LineaFactura
from app.models.inventario import Inventario, MovimientoInventario, TipoMovimiento
from app.models.seguridad import Auditoria, Cuenta, RolCuenta, Sesion
from app.repositories.facturacion import FacturaRepository
from app.repositories.pedidos import PedidoB2BRepository


def _d(valor: Any) -> Decimal:
    """Normaliza un agregado NUMERIC a Decimal, sin pasar por float."""
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def _inicio_dia(valor: date) -> datetime:
    return datetime.combine(valor, time.min)


def _fin_dia(valor: date) -> datetime:
    return datetime.combine(valor, time.max)


class MetricasRepository:
    """Agregados en SQL: una consulta por bloque, nunca una por fila."""

    def __init__(self, db: Session):
        self.db = db

    # ---------- Comunes ----------
    @staticmethod
    def _condiciones_factura(
        desde: date,
        hasta: date,
        cliente_id: int | None = None,
    ) -> list:
        return [
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
            Factura.estado.in_([EstadoFactura.EMITIDA, EstadoFactura.EN_REVISION]),
        ] + ([Factura.cliente_id == cliente_id] if cliente_id is not None else [])

    # ---------- Resumen ----------
    def resumen(
        self,
        desde: date,
        hasta: date,
        ahora: datetime,
        ventana: Any,
    ) -> dict:
        condiciones = self._condiciones_factura(desde, hasta)
        ingresos, facturas = self.db.execute(
            select(
                func.coalesce(func.sum(Factura.total), 0),
                func.count(Factura.id),
            ).where(*condiciones)
        ).one()

        empresas_total = self.db.scalar(
            select(func.count(Cuenta.id)).where(Cuenta.rol == RolCuenta.EMPRESA)
        ) or 0
        empresas_activas = self.db.scalar(
            select(func.count(Cuenta.id)).where(
                Cuenta.rol == RolCuenta.EMPRESA, Cuenta.activo.is_(True)
            )
        ) or 0
        empresas_en_linea = self.db.scalar(
            select(func.count(func.distinct(Sesion.cuenta_id)))
            .join(Cuenta, Cuenta.id == Sesion.cuenta_id)
            .where(
                Cuenta.rol == RolCuenta.EMPRESA,
                Sesion.revocada.is_(False),
                Sesion.expira_en > ahora,
                Sesion.ultima_actividad >= ahora - ventana,
            )
        ) or 0
        pedidos_por_facturar = self.db.scalar(
            select(func.count(PedidoB2B.id)).where(
                PedidoB2B.estado.in_(
                    [EstadoPedido.PENDIENTE, EstadoPedido.PROCESANDO]
                ),
                PedidoB2B.factura_generada_id.is_(None),
            )
        ) or 0
        en_revision = self.db.scalar(
            select(func.count(Factura.id)).where(
                *condiciones,
                or_(
                    Factura.estado == EstadoFactura.EN_REVISION,
                    Factura.en_revision.is_(True),
                ),
            )
        ) or 0
        bajo_minimo = self.db.scalar(
            select(func.count(Inventario.producto_id)).where(
                Inventario.existencias < Inventario.stock_minimo
            )
        ) or 0

        return {
            "empresas_total": int(empresas_total),
            "empresas_activas": int(empresas_activas),
            "empresas_en_linea": int(empresas_en_linea),
            "pedidos_por_facturar": int(pedidos_por_facturar),
            "facturas_en_revision": int(en_revision),
            "productos_bajo_minimo": int(bajo_minimo),
            "ingresos_periodo": _d(ingresos),
            "facturas_periodo": int(facturas),
        }

    # ---------- Ingresos ----------
    def ingresos_mensuales(
        self, hasta: date, inicio_meses: date
    ) -> dict[str, tuple[Decimal, int]]:
        filas = self.db.execute(
            select(
                func.to_char(Factura.fecha, "YYYY-MM").label("mes"),
                func.coalesce(func.sum(Factura.total), 0),
                func.count(Factura.id),
            )
            .where(
                Factura.fecha >= inicio_meses,
                Factura.fecha <= hasta,
                Factura.estado.in_(
                    [EstadoFactura.EMITIDA, EstadoFactura.EN_REVISION]
                ),
            )
            .group_by("mes")
            .order_by("mes")
        ).all()
        return {mes: (_d(ingresos), int(conteo)) for mes, ingresos, conteo in filas}

    def ingresos_por_empresa(
        self, desde: date, hasta: date
    ) -> list[tuple[int | None, str, Decimal, int]]:
        filas = self.db.execute(
            select(
                Factura.cliente_id,
                ClienteB2B.nombre_empresa,
                func.coalesce(func.sum(Factura.total), 0),
                func.count(Factura.id),
            )
            .select_from(Factura)
            .outerjoin(ClienteB2B, ClienteB2B.id == Factura.cliente_id)
            .where(*self._condiciones_factura(desde, hasta))
            .group_by(Factura.cliente_id, ClienteB2B.nombre_empresa)
            .order_by(func.sum(Factura.total).desc(), ClienteB2B.nombre_empresa)
        ).all()
        return [
            (cliente_id, nombre or "Sin empresa", _d(ingresos), int(conteo))
            for cliente_id, nombre, ingresos, conteo in filas
        ]

    def ingresos_por_sector(
        self, desde: date, hasta: date
    ) -> list[tuple[Any, Decimal, int]]:
        filas = self.db.execute(
            select(
                ClienteB2B.sector,
                func.coalesce(func.sum(Factura.total), 0),
                func.count(Factura.id),
            )
            .select_from(Factura)
            .outerjoin(ClienteB2B, ClienteB2B.id == Factura.cliente_id)
            .where(*self._condiciones_factura(desde, hasta))
            .group_by(ClienteB2B.sector)
            .order_by(func.sum(Factura.total).desc())
        ).all()
        return [(sector, _d(ingresos), int(conteo)) for sector, ingresos, conteo in filas]

    def ingresos_por_categoria(
        self, desde: date, hasta: date
    ) -> list[tuple[str, Decimal, int]]:
        nombre_categoria = func.coalesce(
            LineaFactura.categoria, Categoria.nombre, "Sin categoría"
        )
        filas = self.db.execute(
            select(
                nombre_categoria.label("nombre_categoria"),
                func.coalesce(func.sum(LineaFactura.monto), 0),
                func.count(func.distinct(Factura.id)),
            )
            .select_from(Factura)
            .join(LineaFactura, LineaFactura.factura_id == Factura.id)
            .outerjoin(Producto, Producto.id == LineaFactura.producto_id)
            .outerjoin(Categoria, Categoria.id == Producto.categoria_id)
            .where(*self._condiciones_factura(desde, hasta))
            .group_by(nombre_categoria)
            .order_by(func.sum(LineaFactura.monto).desc())
        ).all()
        return [(str(nombre), _d(ingresos), int(conteo)) for nombre, ingresos, conteo in filas]

    # ---------- Productos ----------
    def ventas_productos(
        self,
        desde: date,
        hasta: date,
        cliente_id: int | None = None,
    ) -> list[Any]:
        """Una fila por producto y presentación; el servicio convierte a unidades."""
        ventas = (
            select(
                LineaPedidoB2B.producto_id.label("producto_id"),
                LineaPedidoB2B.tipo_empaque.label("tipo_empaque"),
                Producto.unidades_por_caja.label("unidades_por_caja"),
                func.coalesce(func.sum(LineaPedidoB2B.cantidad), 0).label("cantidad"),
                func.coalesce(func.sum(LineaPedidoB2B.subtotal), 0).label("monto"),
                func.count(func.distinct(PedidoB2B.id)).label("pedidos"),
            )
            .select_from(LineaPedidoB2B)
            .join(PedidoB2B, PedidoB2B.id == LineaPedidoB2B.pedido_id)
            .join(Producto, Producto.id == LineaPedidoB2B.producto_id)
            .where(
                PedidoB2B.fecha_creacion >= _inicio_dia(desde),
                PedidoB2B.fecha_creacion <= _fin_dia(hasta),
                PedidoB2B.estado != EstadoPedido.CANCELADO,
                *([PedidoB2B.cliente_id == cliente_id] if cliente_id is not None else []),
            )
            .group_by(
                LineaPedidoB2B.producto_id,
                LineaPedidoB2B.tipo_empaque,
                Producto.unidades_por_caja,
            )
            .subquery()
        )
        stmt = (
            select(
                Producto.id,
                Producto.nombre,
                Producto.sku,
                Categoria.nombre,
                Categoria.sector,
                ventas.c.tipo_empaque,
                ventas.c.unidades_por_caja,
                ventas.c.cantidad,
                ventas.c.monto,
                ventas.c.pedidos,
            )
            .join(Categoria, Categoria.id == Producto.categoria_id)
            .outerjoin(ventas, ventas.c.producto_id == Producto.id)
            .where(Producto.estado_activo.is_(True))
            .order_by(Producto.nombre, Producto.id)
        )
        return list(self.db.execute(stmt).all())

    # ---------- Empresas ----------
    def _compras(self, desde: date, hasta: date):
        return (
            select(
                Factura.cliente_id.label("cliente_id"),
                func.coalesce(func.sum(Factura.total), 0).label("total"),
                func.max(Factura.fecha).label("ultima"),
            )
            .where(*self._condiciones_factura(desde, hasta))
            .group_by(Factura.cliente_id)
            .subquery()
        )

    @staticmethod
    def _condiciones_empresa(
        sector: SectorEmpresa | None,
        activo: bool | None,
        busqueda: str | None,
    ) -> list:
        condiciones = []
        if sector is not None:
            condiciones.append(ClienteB2B.sector == sector)
        if activo is not None:
            condiciones.append(ClienteB2B.activo.is_(activo))
        if busqueda:
            patron = f"%{busqueda.strip()}%"
            condiciones.append(
                or_(
                    ClienteB2B.nombre_empresa.ilike(patron),
                    ClienteB2B.ruc.ilike(patron),
                )
            )
        return condiciones

    def listar_empresas(
        self,
        desde: date,
        hasta: date,
        sector: SectorEmpresa | None,
        activo: bool | None,
        busqueda: str | None,
        desplazamiento: int,
        limite: int,
    ) -> tuple[list[Any], int]:
        condiciones = self._condiciones_empresa(sector, activo, busqueda)
        total = self.db.scalar(
            select(func.count(ClienteB2B.id)).where(*condiciones)
        ) or 0
        compras = self._compras(desde, hasta)
        cuentas = (
            select(
                Cuenta.cliente_id.label("cliente_id"),
                func.bool_or(Cuenta.activo).label("activo"),
            )
            .where(Cuenta.rol == RolCuenta.EMPRESA)
            .group_by(Cuenta.cliente_id)
            .subquery()
        )
        filas = self.db.execute(
            select(
                ClienteB2B,
                cuentas.c.activo,
                compras.c.total,
                compras.c.ultima,
            )
            .outerjoin(cuentas, cuentas.c.cliente_id == ClienteB2B.id)
            .outerjoin(compras, compras.c.cliente_id == ClienteB2B.id)
            .where(*condiciones)
            .order_by(ClienteB2B.nombre_empresa, ClienteB2B.id)
            .offset(desplazamiento)
            .limit(limite)
        ).all()
        return list(filas), int(total)

    def obtener_empresa(
        self, cliente_id: int, desde: date, hasta: date
    ) -> tuple[ClienteB2B | None, bool, Decimal, date | None, int, int]:
        cliente = self.db.get(ClienteB2B, cliente_id)
        if cliente is None:
            return None, False, Decimal("0.00"), None, 0, 0
        cuenta_activa = bool(
            self.db.scalar(
                select(func.count(Cuenta.id)).where(
                    Cuenta.rol == RolCuenta.EMPRESA,
                    Cuenta.cliente_id == cliente_id,
                    Cuenta.activo.is_(True),
                )
            )
        )
        compras = self._compras(desde, hasta)
        total, ultima = self.db.execute(
            select(compras.c.total, compras.c.ultima).where(
                compras.c.cliente_id == cliente_id
            )
        ).one_or_none() or (0, None)
        pedidos = self.db.scalar(
            select(func.count(PedidoB2B.id)).where(PedidoB2B.cliente_id == cliente_id)
        ) or 0
        facturas = self.db.scalar(
            select(func.count(Factura.id)).where(
                *self._condiciones_factura(desde, hasta, cliente_id)
            )
        ) or 0
        return cliente, cuenta_activa, _d(total), ultima, int(pedidos), int(facturas)

    # ---------- Catálogo ----------
    def categorias(
        self,
        sector: SectorEmpresa | None,
        busqueda: str | None,
        desplazamiento: int,
        limite: int,
    ) -> tuple[list[Any], int]:
        condiciones = []
        if sector is not None:
            condiciones.append(Categoria.sector == sector)
        if busqueda:
            condiciones.append(Categoria.nombre.ilike(f"%{busqueda.strip()}%"))
        total = self.db.scalar(select(func.count(Categoria.id)).where(*condiciones)) or 0
        filas = self.db.execute(
            select(
                Categoria,
                func.count(Producto.id),
            )
            .outerjoin(Producto, Producto.categoria_id == Categoria.id)
            .where(*condiciones)
            .group_by(Categoria.id)
            .order_by(Categoria.nombre)
            .offset(desplazamiento)
            .limit(limite)
        ).all()
        return list(filas), int(total)

    def catalogo_productos(
        self,
        desde: date,
        hasta: date,
        categoria_id: int | None,
        sector: SectorEmpresa | None,
        busqueda: str | None,
        solo_activos: bool,
        desplazamiento: int,
        limite: int,
        producto_id: int | None = None,
    ) -> tuple[list[Any], int]:
        ventas = (
            select(
                LineaPedidoB2B.producto_id.label("producto_id"),
                LineaPedidoB2B.tipo_empaque.label("tipo_empaque"),
                Producto.unidades_por_caja.label("unidades_por_caja"),
                func.coalesce(func.sum(LineaPedidoB2B.cantidad), 0).label("cantidad"),
                func.coalesce(func.sum(LineaPedidoB2B.subtotal), 0).label("monto"),
                func.count(func.distinct(PedidoB2B.id)).label("pedidos"),
            )
            .select_from(LineaPedidoB2B)
            .join(PedidoB2B, PedidoB2B.id == LineaPedidoB2B.pedido_id)
            .join(Producto, Producto.id == LineaPedidoB2B.producto_id)
            .where(
                PedidoB2B.fecha_creacion >= _inicio_dia(desde),
                PedidoB2B.fecha_creacion <= _fin_dia(hasta),
                PedidoB2B.estado != EstadoPedido.CANCELADO,
            )
            .group_by(
                LineaPedidoB2B.producto_id,
                LineaPedidoB2B.tipo_empaque,
                Producto.unidades_por_caja,
            )
            .subquery()
        )
        condiciones = []
        if categoria_id is not None:
            condiciones.append(Producto.categoria_id == categoria_id)
        if sector is not None:
            condiciones.append(Categoria.sector == sector)
        if busqueda:
            patron = f"%{busqueda.strip()}%"
            condiciones.append(
                or_(Producto.nombre.ilike(patron), Producto.sku.ilike(patron))
            )
        if solo_activos:
            condiciones.append(Producto.estado_activo.is_(True))
        if producto_id is not None:
            condiciones.append(Producto.id == producto_id)

        total = self.db.scalar(
            select(func.count(Producto.id))
            .join(Categoria, Categoria.id == Producto.categoria_id)
            .where(*condiciones)
        ) or 0
        columnas = (
            Producto,
            Categoria.nombre,
            Categoria.sector,
            Inventario.existencias,
            Inventario.stock_minimo,
            ventas.c.tipo_empaque,
            ventas.c.unidades_por_caja,
            ventas.c.cantidad,
            ventas.c.monto,
            ventas.c.pedidos,
        )
        consulta = (
            select(*columnas)
            .join(Categoria, Categoria.id == Producto.categoria_id)
            .outerjoin(Inventario, Inventario.producto_id == Producto.id)
            .outerjoin(ventas, ventas.c.producto_id == Producto.id)
            .where(*condiciones)
            .order_by(Producto.nombre, Producto.id)
        )
        if producto_id is None:
            consulta = consulta.offset(desplazamiento).limit(limite)
        return list(self.db.execute(consulta).all()), int(total)

    # ---------- Pedidos ----------
    def listar_pedidos(
        self,
        desde: date,
        hasta: date,
        estado: EstadoPedido | None,
        cliente_id: int | None,
        desplazamiento: int,
        limite: int,
    ) -> tuple[list[PedidoB2B], int]:
        condiciones = [
            PedidoB2B.fecha_creacion >= _inicio_dia(desde),
            PedidoB2B.fecha_creacion <= _fin_dia(hasta),
        ]
        if estado is not None:
            condiciones.append(PedidoB2B.estado == estado)
        if cliente_id is not None:
            condiciones.append(PedidoB2B.cliente_id == cliente_id)
        total = self.db.scalar(
            select(func.count(PedidoB2B.id)).where(*condiciones)
        ) or 0
        pedidos = self.db.scalars(
            select(PedidoB2B)
            .options(
                selectinload(PedidoB2B.lineas),
                selectinload(PedidoB2B.cliente),
            )
            .where(*condiciones)
            .order_by(PedidoB2B.fecha_creacion.desc(), PedidoB2B.id.desc())
            .offset(desplazamiento)
            .limit(limite)
        ).all()
        return list(pedidos), int(total)

    def ultimas_facturas(self, cliente_id: int, limite: int = 5) -> list[Factura]:
        return FacturaRepository.listar(
            self.db, cliente_id=cliente_id, skip=0, limit=limite
        )

    def ultimos_pedidos(self, cliente_id: int, limite: int = 5) -> list[PedidoB2B]:
        return PedidoB2BRepository(self.db).listar(
            cliente_id=cliente_id, skip=0, limit=limite
        )

    # ---------- Inventario y auditoría ----------
    def movimientos(
        self,
        producto_id: int | None,
        tipo: TipoMovimiento | None,
        desde: date,
        hasta: date,
        desplazamiento: int,
        limite: int,
    ) -> tuple[list[MovimientoInventario], int]:
        condiciones = [
            MovimientoInventario.fecha >= _inicio_dia(desde),
            MovimientoInventario.fecha <= _fin_dia(hasta),
        ]
        if producto_id is not None:
            condiciones.append(MovimientoInventario.producto_id == producto_id)
        if tipo is not None:
            condiciones.append(MovimientoInventario.tipo == tipo)
        total = self.db.scalar(
            select(func.count(MovimientoInventario.id)).where(*condiciones)
        ) or 0
        filas = self.db.scalars(
            select(MovimientoInventario)
            .where(*condiciones)
            .order_by(
                MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc()
            )
            .offset(desplazamiento)
            .limit(limite)
        ).all()
        return list(filas), int(total)

    def auditoria(
        self,
        accion: str | None,
        cuenta_id: int | None,
        desde: date,
        hasta: date,
        desplazamiento: int,
        limite: int,
    ) -> tuple[list[Auditoria], int]:
        condiciones = [
            Auditoria.fecha >= _inicio_dia(desde),
            Auditoria.fecha <= _fin_dia(hasta),
        ]
        if accion:
            condiciones.append(Auditoria.accion.ilike(f"%{accion.strip()}%"))
        if cuenta_id is not None:
            condiciones.append(Auditoria.cuenta_id == cuenta_id)
        total = self.db.scalar(select(func.count(Auditoria.id)).where(*condiciones)) or 0
        filas = self.db.scalars(
            select(Auditoria)
            .where(*condiciones)
            .order_by(Auditoria.fecha.desc(), Auditoria.id.desc())
            .offset(desplazamiento)
            .limit(limite)
        ).all()
        return list(filas), int(total)
