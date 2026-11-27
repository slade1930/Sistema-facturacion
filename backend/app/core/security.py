import hmac
import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.constants import API_KEY_ENV, API_KEY_HEADER
from app.core.logging import get_logger

logger = get_logger(__name__)

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)

def obtener_api_key_configurada():
    return os.getenv(API_KEY_ENV, "").strip()


def claves_coinciden(recibida, esperada):
    if not recibida or not esperada:
        return False
    return hmac.compare_digest(
        recibida.encode("utf-8"), esperada.encode("utf-8")
    )
def verificar_api_key(api_key=Security(_api_key_header)):
    esperada = obtener_api_key_configurada()
    if not esperada:
        logger.error("API_KEY no está configurada en el servidor.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La API_KEY no está configurada en el servidor.",
        )
    if not claves_coinciden(api_key, esperada):
        logger.warning("Petición rechazada: X-API-Key ausente o inválida.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente o inválida.",
        )