"""Cabeceras de seguridad y CORS restrictivo para la API.

Los orígenes se leen de ``CORS_ORIGINES`` en cada petición: una lista separada
por comas con orígenes explícitos (esquema, host y puerto). El comodín ``*`` se
ignora; nunca se devuelve como origen permitido.
"""

import os

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORS_ORIGINES_ENV = "CORS_ORIGINES"

CABECERAS_SEGURIDAD = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}
METODOS_PERMITIDOS = "GET, POST, PUT, DELETE, OPTIONS"
CABECERAS_PERMITIDAS = "Authorization, Content-Type, X-API-Key"


def _origenes_configurados() -> set[str]:
    crudo = os.getenv(CORS_ORIGINES_ENV, "")
    return {
        parte.rstrip("/")
        for parte in (fragmento.strip() for fragmento in crudo.split(","))
        if parte and "*" not in parte
    }


def _cabecera(scope: Scope, nombre: bytes) -> str | None:
    for clave, valor in scope.get("headers", []):
        if clave.lower() == nombre:
            return valor.decode("latin-1")
    return None


def _agregar_vary(valor_actual: str | None) -> str:
    partes = [
        parte.strip() for parte in (valor_actual or "").split(",") if parte.strip()
    ]
    if "Origin" not in partes:
        partes.append("Origin")
    return ", ".join(partes)


def _es_ruta_auth(ruta: str) -> bool:
    return "auth" in ruta.split("/")


class CabecerasSeguridadMiddleware:
    """Aplica cabeceras de seguridad y responde el preflight CORS permitido."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origen_recibido = _cabecera(scope, b"origin")
        origenes = _origenes_configurados()
        origen = origen_recibido if origen_recibido in origenes else None

        if (
            scope.get("method") == "OPTIONS"
            and origen is not None
            and _cabecera(scope, b"access-control-request-method")
        ):
            await self._preflight(scope, send, origen)
            return

        async def enviar(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                cabeceras = MutableHeaders(scope=mensaje)
                self._aplicar(cabeceras, scope["path"], origen)
            await send(mensaje)

        await self.app(scope, receive, enviar)

    async def _preflight(
        self, scope: Scope, send: Send, origen: str
    ) -> None:
        cabeceras = MutableHeaders()
        self._aplicar(cabeceras, scope["path"], origen)
        cabeceras["access-control-allow-methods"] = METODOS_PERMITIDOS
        cabeceras["access-control-allow-headers"] = CABECERAS_PERMITIDAS
        cabeceras["access-control-max-age"] = "600"
        await send(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": cabeceras.raw,
            }
        )
        await send({"type": "http.response.body", "body": b""})

    def _aplicar(
        self, cabeceras: MutableHeaders, ruta: str, origen: str | None
    ) -> None:
        for nombre, valor in CABECERAS_SEGURIDAD.items():
            cabeceras[nombre] = valor
        if _es_ruta_auth(ruta):
            cabeceras["cache-control"] = "no-store"
        if origen is not None:
            cabeceras["access-control-allow-origin"] = origen
            cabeceras["vary"] = _agregar_vary(cabeceras.get("vary"))
