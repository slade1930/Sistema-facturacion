"""Entrada y salida de login, registro y sesión. Empresa y admin; etapa A."""

from pydantic import BaseModel, Field

from app.schemas.empresa import EmpresaResumen


class LoginEntrada(BaseModel):
    nombre_empresa: str = Field(min_length=1, max_length=200)
    contrasena: str = Field(min_length=1, max_length=64)


class CambiarClaveEntrada(BaseModel):
    contrasena_actual: str = Field(min_length=1, max_length=64)
    contrasena_nueva: str = Field(min_length=1, max_length=64)


class SesionSalida(BaseModel):
    token: str
    tipo: str = "Bearer"
    rol: str
    cuenta_id: int
    empresa: EmpresaResumen | None = None
    debe_cambiar_clave: bool


class YoSalida(BaseModel):
    rol: str
    cuenta_id: int
    empresa: EmpresaResumen | None = None
    debe_cambiar_clave: bool


class MensajeSalida(BaseModel):
    detalle: str
