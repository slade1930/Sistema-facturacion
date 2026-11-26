import os

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.constants import API_KEY_ENV, API_KEY_HEADER
from app.core.security import verificar_api_key
from app.db.session import get_db

_API_KEY_DEV = "dev-api-key-cambiar"
_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def requiere_auth(api_key: str | None = Security(_api_key_header)) -> None:
    if not os.getenv(API_KEY_ENV, "").strip():
        os.environ.setdefault(API_KEY_ENV, _API_KEY_DEV)
    verificar_api_key(api_key)
