import os
from typing import Any

import httpx

RUTAS_PUBLICAS = (
    "/health",
    "/api/v1/verificar",
)


class ErrorApi(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.errors = errors or []


class ClienteApi:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        token: str | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("BACKEND_URL", "http://localhost:8000")
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("API_KEY", "")
        self.timeout = timeout
        self.token = token
        self._client = client
        self._cerrar = client is None

    def __enter__(self) -> "ClienteApi":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cerrar()

    def cerrar(self) -> None:
        if self._cerrar and self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _headers(self, ruta: str) -> dict[str, str]:
        if any(ruta.startswith(publica) for publica in RUTAS_PUBLICAS):
            return {}
        cabeceras = {"X-API-Key": self.api_key}
        if self.token:
            cabeceras["Authorization"] = f"Bearer {self.token}"
        return cabeceras

    def request(
        self,
        metodo: str,
        ruta: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
    ) -> Any:
        opciones: dict[str, Any] = {}
        if params is not None:
            opciones["params"] = params
        if json is not None:
            opciones["json"] = json
        if data is not None:
            opciones["data"] = data
        if files is not None:
            opciones["files"] = files

        respuesta = self.client.request(
            metodo,
            f"{self.base_url}{ruta}",
            headers=self._headers(ruta),
            **opciones,
        )
        if respuesta.is_success:
            if respuesta.status_code == 204:
                return None
            if "application/json" in respuesta.headers.get("content-type", ""):
                return respuesta.json()
            return respuesta.content
        return self._lanzar(respuesta)

    def _lanzar(self, respuesta: httpx.Response) -> None:
        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}
        detail = cuerpo.get("detail") or respuesta.text or "Error inesperado."
        code = cuerpo.get("code") or "ERROR"
        errors = cuerpo.get("errors", [])
        raise ErrorApi(respuesta.status_code, str(detail), str(code), errors)

    def get(self, ruta: str, **kwargs: Any) -> Any:
        return self.request("GET", ruta, **kwargs)

    def post(self, ruta: str, **kwargs: Any) -> Any:
        return self.request("POST", ruta, **kwargs)

    def put(self, ruta: str, **kwargs: Any) -> Any:
        return self.request("PUT", ruta, **kwargs)

    def delete(self, ruta: str, **kwargs: Any) -> Any:
        return self.request("DELETE", ruta, **kwargs)
