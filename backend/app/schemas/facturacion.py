from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.facturacion import CobrarPor, CondicionPago, EstadoFactura


# ==========================================
# Líneas de Factura
# ==========================================
class LineaFacturaBase(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=300)
    codigo_barras: Optional[str] = Field(default=None, max_length=100)
    categoria: Optional[str] = Field(default=None, max_length=120)
    cantidad: Decimal = Field(..., ge=Decimal("0.01"))
    precio_unitario: Decimal = Field(..., ge=Decimal("0.00"))
    precio_unidad: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    descuento_pct: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00")
    )
    gravada: bool = True
    unidades_por_caja: int = Field(default=1, ge=1)
    cobrar_por: CobrarPor = CobrarPor.UNIDAD
    producto_id: Optional[int] = None


class LineaFacturaCreate(LineaFacturaBase):
    orden: Optional[int] = Field(default=None, ge=1)


class LineaFacturaRead(LineaFacturaBase):
    id: int
    factura_id: int
    orden: int
    monto: Decimal

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Factura
# ==========================================
class FacturaCreate(BaseModel):
    fecha: Optional[date] = None
    cliente_nombre: str = Field(..., min_length=1, max_length=200)
    cliente_ruc: Optional[str] = Field(default=None, max_length=40)
    mostrar_ruc: bool = True
    cliente_direccion: Optional[str] = Field(default=None, max_length=250)
    cliente_telefono: Optional[str] = Field(default=None, max_length=60)
    cliente_correo: Optional[str] = Field(default=None, max_length=254)
    sucursal: Optional[str] = Field(default=None, max_length=150)
    vendedor: Optional[str] = Field(default=None, max_length=150)
    orden_compra: Optional[str] = Field(default=None, max_length=60)
    condicion_pago: CondicionPago = CondicionPago.CONTADO
    portes: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    notas: Optional[str] = None
    lineas: list[LineaFacturaCreate] = Field(..., min_length=1)


class FacturaRead(BaseModel):
    id: int
    numero_serie: str
    codigo_verificacion: str
    fecha: date

    cliente_nombre: str
    cliente_ruc: Optional[str] = None
    mostrar_ruc: bool
    cliente_direccion: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_correo: Optional[str] = None
    sucursal: Optional[str] = None
    vendedor: Optional[str] = None
    orden_compra: Optional[str] = None
    condicion_pago: CondicionPago
    portes: Decimal
    notas: Optional[str] = None

    subtotal: Decimal
    descuento_total: Decimal
    base_gravada: Decimal
    base_exenta: Decimal
    itbms: Decimal
    total: Decimal

    estado: EstadoFactura
    en_revision: bool = False
    puntaje_anomalia: Optional[Decimal] = None
    motivo_anomalia: Optional[str] = None
    fecha_creacion: datetime
    fecha_anulacion: Optional[datetime] = None
    lineas: list[LineaFacturaRead] = []

    model_config = ConfigDict(from_attributes=True)


class FacturaResumen(BaseModel):
    id: int
    numero_serie: str
    fecha: date
    cliente_nombre: str
    condicion_pago: CondicionPago
    total: Decimal
    estado: EstadoFactura
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class FacturaVerificacion(BaseModel):
    valida: bool
    numero_serie: str
    codigo_verificacion: str
    fecha: date
    cliente_nombre: str
    total: Decimal
    estado: EstadoFactura


# ==========================================
# Configuración del Negocio
# ==========================================
class ConfiguracionNegocioBase(BaseModel):
    empresa_nombre: str = Field(..., min_length=1, max_length=150)
    empresa_ruc: str = Field(..., min_length=1, max_length=40)
    mostrar_ruc: bool = True
    empresa_direccion: Optional[str] = None
    empresa_correo: Optional[str] = Field(default=None, max_length=254)
    empresa_telefono: Optional[str] = Field(default=None, max_length=60)
    logo: Optional[str] = Field(default=None, max_length=100)
    color_principal: str = Field(default="#3A0088", min_length=4, max_length=7)
    color_barra_factura: str = Field(default="#5B3A9E", min_length=4, max_length=7)
    color_tabla: str = Field(default="#3A0088", min_length=4, max_length=7)
    datos_bancarios: Optional[str] = None
    notas_predeterminadas: Optional[str] = None


class ConfiguracionNegocioUpdate(BaseModel):
    empresa_nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    empresa_ruc: Optional[str] = Field(default=None, min_length=1, max_length=40)
    mostrar_ruc: Optional[bool] = None
    empresa_direccion: Optional[str] = None
    empresa_correo: Optional[str] = Field(default=None, max_length=254)
    empresa_telefono: Optional[str] = Field(default=None, max_length=60)
    logo: Optional[str] = Field(default=None, max_length=100)
    color_principal: Optional[str] = Field(default=None, min_length=4, max_length=7)
    color_barra_factura: Optional[str] = Field(default=None, min_length=4, max_length=7)
    color_tabla: Optional[str] = Field(default=None, min_length=4, max_length=7)
    datos_bancarios: Optional[str] = None
    notas_predeterminadas: Optional[str] = None


class ConfiguracionNegocioRead(ConfiguracionNegocioBase):
    id: int
    actualizado: datetime

    model_config = ConfigDict(from_attributes=True)
