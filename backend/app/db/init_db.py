from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"
ARCHIVO_CONFIG = ALEMBIC_DIR / "alembic.ini"

def init_db() -> None:
    """Aplica todas las migraciones. Unica forma permitida de crear tablas."""
    config = Config(str(ARCHIVO_CONFIG))
    command.upgrade(config, "head")

def probar_conexion() -> bool:
    """Prueba de solo lectura: SELECT 1. No modifica la base."""
    from sqlalchemy import text

    from app.db.session import get_engine

    with get_engine().connect() as conexion:
        return conexion.execute(text("SELECT 1")).scalar_one() == 1