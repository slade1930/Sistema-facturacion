"""Esquemas del panel y la administración global. Rol admin; etapa C1."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.catalogo import SectorEmpresa
from app.models.inventario import TipoMovimiento
from app.schemas.catalogo import CategoriaRead, ProductoCreate, ProductoRead, ProductoUpdate
from app.schemas.facturacion import FacturaResumen
from app.schemas.pedidos import PedidoB2BRead

DineroStock = Decimal  # NUMERIC(14,2), sin redondeo adicional en la API.
Dinero = Decimal


class InventarioRead(BaseModel):
    producto_id: int
    nombre_producto: str
    sku: str
    existencias: Decimal
    stock_minimo: Decimal
    actualizado_en: datetime | None = None


class InventarioActualizar(BaseModel):
    existencias: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    stock_minimo: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2
    )
    motivo: str | None = Field(default=None, max_length=200)


class MovimientoInventarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    fecha: datetime
    tipo: TipoMovimiento
    cantidad: Decimal
    motivo: str
    factura_id: int | None = None
    cuenta_id: int | None = None


# ---------- Panel ----------
class PanelResumen(BaseModel):
    generado_en: datetime
    desde: date
    hasta: date
    empresas_total: int
    empresas_activas: int
    empresas_en_linea: int
    pedidos_por_facturar: int
    facturas_en_revision: int
    productos_bajo_minimo: int
    ingresos_periodo: Decimal
    facturas_periodo: int


class IngresoMes(BaseModel):
    mes: str
    ingresos: Decimal
    facturas: int


class IngresoEmpresa(BaseModel):
    empresa_id: int | None
    nombre: str
    ingresos: Decimal
    facturas: int


class IngresoGrupo(BaseModel):
    nombre: str
    ingresos: Decimal
    facturas: int


class IngresosDesglose(BaseModel):
    desde: date
    hasta: date
    por_mes: list[IngresoMes]
    por_empresa: list[IngresoEmpresa]
    por_sector: list[IngresoGrupo]
    por_categoria: list[IngresoGrupo]


class ProductoRanking(BaseModel):
    producto_id: int
    nombre: str
    sku: str
    unidades: Decimal
    monto: Decimal
    pedidos: int


class ProductosRanking(BaseModel):
    desde: date
    hasta: date
    mas_pedidos_por_unidades: list[ProductoRanking]
    mas_pedidos_por_monto: list[ProductoRanking]
    menos_pedidos: list[ProductoRanking]


# ---------- Empresas ----------
class EmpresaResumen(BaseModel):
    id: int
    nombre_empresa: str
    ruc: str
    sector: SectorEmpresa | None = None
    activo: bool
    cuenta_activa: bool
    total_comprado: Decimal
    fecha_ultima_compra: date | None = None


class EmpresaDetalle(EmpresaResumen):
    direccion: str | None = None
    telefono: str | None = None
    email_contacto: str
    sucursal: str | None = None
    fecha_registro: datetime
    ingresos: Decimal
    pedidos_totales: int
    facturas_totales: int
    productos_mas_comprados: list[ProductoRanking]
    ultimas_facturas: list[FacturaResumen]
    ultimos_pedidos: list[PedidoB2BRead]


class EstadoEmpresa(BaseModel):
    activo: bool
    motivo: str | None = Field(default=None, max_length=200)


# ---------- Catálogo ----------
class ProductoAdminCreate(ProductoCreate):
    existencias_iniciales: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )


class ProductoAdminUpdate(ProductoUpdate):
    # En administración la categoría siempre se envía: define el sector visible.
    categoria_id: int = Field(gt=0)
    existencias: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )


class ProductoAdminRead(ProductoRead):
    categoria_nombre: str
    sector: SectorEmpresa | None = None
    existencias: Decimal
    stock_minimo: Decimal
    ventas_unidades: Decimal
    ventas_monto: Decimal
    pedidos: int


class CategoriaAdminRead(CategoriaRead):
    total_productos: int


class EstadoProducto(BaseModel):
    activo: bool


# ---------- Pedidos y auditoría ----------
class PedidoAdminRead(PedidoB2BRead):
    nombre_empresa: str | None = None


class AuditoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    cuenta_id: int | None = None
    accion: str
    detalle: str | None = None
    ip: str | None = None
