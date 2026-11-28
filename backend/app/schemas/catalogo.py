from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.catalogo import SectorEmpresa

# Dinero: NUMERIC(14,2) en la base. Siempre Decimal, nunca float.
Dinero = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
DineroCorto = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Descuento = Annotated[
    Decimal, Field(ge=0, le=90, max_digits=5, decimal_places=2)
]


def _validar_imagen(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    if not limpio:
        return None
    if ".." in limpio or "\\" in limpio:
        raise ValueError("Ruta de imagen no permitida.")
    if limpio.startswith(("http://", "https://", "media/")):
        return limpio
    raise ValueError("La imagen debe ser una ruta en 'media/' o una URL válida.")


# ---------- Categoría ----------
class CategoriaBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    sector: SectorEmpresa | None = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    sector: SectorEmpresa | None = None


class CategoriaRead(CategoriaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Producto ----------
class ProductoBase(BaseModel):
    categoria_id: int
    nombre: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=50)
    codigo_barras: str | None = Field(default=None, max_length=50)
    descripcion_corta: str | None = Field(default=None, max_length=500)
    marca: str | None = Field(default=None, max_length=100)
    presentacion: str | None = Field(default=None, max_length=50)
    imagen: str | None = Field(default=None, max_length=100)
    precio_caja: Dinero
    precio_media_caja: Dinero | None = None
    permite_media_caja: bool = False
    precio_unidad: Dinero
    precio_consumidor: DineroCorto | None = None
    unidades_por_caja: int = Field(default=1, ge=1)
    descuento_pct: Descuento = Decimal("0.00")
    aplica_itbms: bool = True  # ITBMS 7 % solo si es gravado
    estado_activo: bool = True

    @field_validator("imagen")
    @classmethod
    def validar_imagen_base(cls, v: str | None) -> str | None:
        return _validar_imagen(v)


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    categoria_id: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    codigo_barras: str | None = Field(default=None, max_length=50)
    descripcion_corta: str | None = Field(default=None, max_length=500)
    marca: str | None = Field(default=None, max_length=100)
    presentacion: str | None = Field(default=None, max_length=50)
    imagen: str | None = Field(default=None, max_length=100)
    precio_caja: Dinero | None = None
    precio_media_caja: Dinero | None = None
    permite_media_caja: bool | None = None
    precio_unidad: Dinero | None = None
    precio_consumidor: DineroCorto | None = None
    unidades_por_caja: int | None = Field(default=None, ge=1)
    descuento_pct: Descuento | None = None
    aplica_itbms: bool | None = None
    estado_activo: bool | None = None

    @field_validator("imagen")
    @classmethod
    def validar_imagen_update(cls, v: str | None) -> str | None:
        return _validar_imagen(v)


class ProductoRead(ProductoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime


# ---------- Cliente B2B ----------
class ClienteB2BBase(BaseModel):
    nombre_empresa: str = Field(min_length=1, max_length=200)
    ruc: str = Field(min_length=1, max_length=40)
    email_contacto: str = Field(min_length=3, max_length=254)
    telefono: str | None = Field(default=None, max_length=60)
    direccion: str | None = None
    sucursal: str | None = Field(default=None, max_length=150)
    sector: SectorEmpresa | None = None
    activo: bool = True


class ClienteB2BCreate(ClienteB2BBase):
    pass


class ClienteB2BUpdate(BaseModel):
    nombre_empresa: str | None = Field(default=None, min_length=1, max_length=200)
    ruc: str | None = Field(default=None, min_length=1, max_length=40)
    email_contacto: str | None = Field(default=None, min_length=3, max_length=254)
    telefono: str | None = Field(default=None, max_length=60)
    direccion: str | None = None
    sucursal: str | None = Field(default=None, max_length=150)
    sector: SectorEmpresa | None = None
    activo: bool | None = None


class ClienteB2BRead(ClienteB2BBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha_registro: datetime
