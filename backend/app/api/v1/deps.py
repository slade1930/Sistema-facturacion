from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.core.constants import API_KEY_HEADER
from app.core.security import (
    claves_coinciden,
    obtener_api_key_configurada,
    verificar_api_key,
)
from app.db.session import get_db
from app.models.seguridad import RolCuenta
from app.services.auth import ip_de_la_peticion, obtener_sesion_valida

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)
SIN_PERMISO = "No tienes permiso para esta acción."


@dataclass(frozen=True)
class Actor:
    rol: str
    cuenta_id: int | None = None
    cliente_id: int | None = None
    nombre_usuario: str | None = None
    token: str | None = None
    sector: str | None = None

    @property
    def es_sistema(self) -> bool:
        return self.rol == "sistema"

    @property
    def es_admin(self) -> bool:
        return self.rol in ("admin", "sistema")

    @property
    def es_empresa(self) -> bool:
        return self.rol == "empresa"


def _token_bearer(autorizacion: str | None) -> str | None:
    if not autorizacion:
        return None
    partes = autorizacion.strip().split()
    if len(partes) != 2 or partes[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada.",
        )
    return partes[1]


def get_actor(
    request: Request,
    api_key: str | None = Security(_api_key_header),
    autorizacion: str | None = Header(default=None, alias="Authorization"),
    db=Depends(get_db),
) -> Actor:
    """Valida X-API-Key y, si viene, el token Bearer opcional."""
    verificar_api_key(api_key)
    token = _token_bearer(autorizacion)
    if token is None:
        # API-Key válida sin token: actor de sistema para pruebas y procesos internos.
        return Actor(rol="sistema")

    sesion = obtener_sesion_valida(db, token)
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada.",
        )
    cuenta, _ = sesion
    if cuenta.rol == RolCuenta.ADMIN:
        return Actor(
            rol="admin", cuenta_id=cuenta.id, nombre_usuario=cuenta.nombre_usuario, token=token
        )
    if cuenta.rol == RolCuenta.EMPRESA and cuenta.cliente_id is not None:
        cliente = cuenta.cliente
        sector = None
        if cliente is not None and cliente.sector is not None:
            sector = getattr(cliente.sector, "value", cliente.sector)
        return Actor(
            rol="empresa",
            cuenta_id=cuenta.id,
            cliente_id=cuenta.cliente_id,
            nombre_usuario=cuenta.nombre_usuario,
            token=token,
            sector=sector,
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada.",
    )


def requiere_auth(actor: Actor = Depends(get_actor)) -> None:
    """Compatibilidad con los routers actuales: exige API-Key o sesión válida."""
    return None


def requiere_admin(actor: Actor = Depends(get_actor)) -> Actor:
    if not actor.es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para esta acción.",
        )
    return actor


def requiere_empresa(actor: Actor = Depends(get_actor)) -> Actor:
    if not actor.es_empresa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción es solo para empresas.",
        )
    return actor


def requiere_empresa_o_admin(actor: Actor = Depends(get_actor)) -> Actor:
    """Recomendaciones: empresa ve lo suyo; admin y sistema, todo."""
    if not (actor.es_empresa or actor.es_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=SIN_PERMISO
        )
    return actor


def ip_para_limite(request: Request, api_key: str | None) -> str:
    """Acepta X-Forwarded-For solo cuando la API-Key recibida es válida."""
    confiar = bool(
        api_key and claves_coinciden(api_key, obtener_api_key_configurada())
    )
    return ip_de_la_peticion(request, confiar)
