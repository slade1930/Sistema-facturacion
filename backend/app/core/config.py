from pydantic_settings import BaseSettings, SettingsConfigDict


# Gente, esto lo puse acá para que se guíen de cómo se leen las variables de entorno.
# En Docker el compose ya manda DATABASE_URL; afuera pueden usar un .env en backend/.
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://factura:factura@localhost:5432/factura"
    # URL pública base del backend para el QR de verificación de facturas.
    # pdf.py le agrega /api/v1/verificar/<serie>/<codigo>. En producción se
    # sobrescribe por entorno/.env con el dominio real.
    FACTURA_VERIFICACION_BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
