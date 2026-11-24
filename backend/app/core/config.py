from pydantic_settings import BaseSettings, SettingsConfigDict


# Gente, esto lo puse acá para que se guíen de cómo se leen las variables de entorno.
# En Docker el compose ya manda DATABASE_URL; afuera pueden usar un .env en backend/.
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://factura:factura@localhost:5432/factura"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
