import os

from pydantic_settings import BaseSettings, SettingsConfigDict


# Gente, esto lo puse acá para que se guíen de cómo se leen las variables de entorno.
# En Docker el compose ya manda DATABASE_URL; afuera pueden usar un .env en backend/.
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://factura:factura@localhost:5432/factura"
    FACTURA_HMAC_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


def validar_factura_hmac_key() -> None:
    """Comprueba la clave HMAC al arrancar, sin mostrarla ni guardarla en logs."""
    clave = (os.getenv("FACTURA_HMAC_KEY") or settings.FACTURA_HMAC_KEY or "").strip()
    if not clave:
        raise RuntimeError(
            "FACTURA_HMAC_KEY no está configurada; no se pueden firmar facturas."
        )
    os.environ.setdefault("FACTURA_HMAC_KEY", clave)
