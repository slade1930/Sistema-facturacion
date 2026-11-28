"""Datos de registro y panel de la empresa. Rol empresa; etapa A."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.catalogo import SectorEmpresa


class EmpresaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ruc: str
    sector: SectorEmpresa | None = None
    sucursal: str | None = None


def resumen_empresa(cliente) -> EmpresaResumen:
    """Arma el resumen de empresa que devuelve la sesión."""
    return EmpresaResumen(
        id=cliente.id,
        nombre=cliente.nombre_empresa,
        ruc=cliente.ruc,
        sector=cliente.sector,
        sucursal=cliente.sucursal,
    )


class EmpresaRegistro(BaseModel):
    nombre_empresa: str = Field(min_length=1, max_length=200)
    ruc: str = Field(min_length=1, max_length=40)
    direccion: str | None = Field(default=None, max_length=250)
    telefono: str | None = Field(default=None, max_length=60)
    correo: str = Field(min_length=1, max_length=254)
    sucursal: str | None = Field(default=None, max_length=150)
    contrasena: str = Field(min_length=1, max_length=64)
    sector: SectorEmpresa
