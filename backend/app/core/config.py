import hashlib
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import API_KEY_ENV


# Gente, esto lo puse acá para que se guíen de cómo se leen las variables de entorno.
# En Docker el compose ya manda DATABASE_URL; afuera pueden usar un .env en backend/.
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://factura:factura@localhost:5432/factura"
    # URL pública base del backend para el QR de verificación de facturas.
    # pdf.py le agrega /api/v1/verificar/<serie>/<codigo>. En producción se
    # sobrescribe por entorno/.env con el dominio real.
    FACTURA_VERIFICACION_BASE_URL: str = "http://localhost:8000"
    # Iteraciones de PBKDF2 para las claves del portal. Solo bajar en pruebas.
    AUTH_PBKDF2_ITERATIONS: int = 600_000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

# Gente, guardo solo el hash del valor viejo de desarrollo para no dejarlo escrito.
HASH_CLAVE_VIEJA = "0d050a511946337c5a00791a33d6c26a6c852d04a00ddbdb0e7567f447d48415"


def validar_api_key() -> None:
    """Comprueba la API_KEY al arrancar, sin mostrarla ni guardarla en logs."""
    if not (os.getenv(API_KEY_ENV) or "").strip():
        raise RuntimeError(
            "API_KEY no está configurada; no se puede arrancar la API."
        )


def validar_factura_hmac_key() -> None:
    """Comprueba la clave HMAC al arrancar, sin mostrarla ni guardarla en logs."""
    clave = (os.getenv("FACTURA_HMAC_KEY") or "").strip()
    if not clave:
        raise RuntimeError(
            "FACTURA_HMAC_KEY no está configurada; no se pueden firmar facturas."
        )
    if hashlib.sha256(clave.encode("utf-8")).hexdigest() == HASH_CLAVE_VIEJA:
        raise RuntimeError(
            "FACTURA_HMAC_KEY usa el valor viejo de desarrollo; definí una clave propia."
        )
