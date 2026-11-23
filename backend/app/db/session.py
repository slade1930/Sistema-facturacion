import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

URL_POR_DEFECTO = "postgresql+psycopg://postgres:postgres@localhost:5432/facturacion"

_engine = None
_SessionLocal = None

def get_engine():
    """Crea el motor solo cuando se usa. Asi los tests con SQLite no necesitan psycopg."""
    url = os.getenv("DATABASE_URL", URL_POR_DEFECTO)
    return create_engine(url, pool_pre_ping=True, future=True)

def get_session_local():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SessionLocal

def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()