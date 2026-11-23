from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Paginacion(BaseModel):
    limite: int = Field(default=20, ge=1, le=100)
    desplazamiento: int = Field(default=0, ge=0)


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limite: int
    desplazamiento: int


class Mensaje(BaseModel):
    detalle: str