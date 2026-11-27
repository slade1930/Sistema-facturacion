from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.constants import API_KEY_HEADER
from app.core.security import verificar_api_key
from app.db.session import get_db

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def requiere_auth(api_key: str | None = Security(_api_key_header)) -> None:
    verificar_api_key(api_key)
