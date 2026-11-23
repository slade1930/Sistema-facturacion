import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

URL_POR_DEFECTO = settings.DATABASE_URL

_engine = None
_SessionLocal = None


def get_engine():
    """Crea el motor una sola vez. La URL viene del entorno o de settings."""
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL", URL_POR_DEFECTO)
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


class _EngineProxy:
    """Para que app.main pueda importar `engine` sin crearlo al importar."""

    def __getattr__(self, nombre):
        return getattr(get_engine(), nombre)

    def connect(self, *args, **kwargs):
        return get_engine().connect(*args, **kwargs)

    def begin(self, *args, **kwargs):
        return get_engine().begin(*args, **kwargs)


engine = _EngineProxy()


class _SessionLocalProxy:
    """Mantiene disponible `SessionLocal` para el código de la API."""

    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)

    def __getattr__(self, nombre):
        return getattr(get_session_local(), nombre)


SessionLocal = _SessionLocalProxy()


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
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