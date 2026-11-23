"""Registro unico de modelos para que Alembic vea todas las tablas."""

from . import facturacion  # noqa: F401

__all__ = ["facturacion"]