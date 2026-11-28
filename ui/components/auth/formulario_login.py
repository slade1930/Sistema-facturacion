"""Campos del inicio de sesión del portal; etapa B."""

from typing import Any

from components.forms import campo_orquidea


def campos_login() -> dict[str, Any]:
    """Devuelve los campos de empresa y contraseña dentro del contexto actual."""
    return {
        "empresa": campo_orquidea(
            "Empresa", placeholder="Nombre con el que te registraste"
        ),
        "contrasena": campo_orquidea(
            "Contraseña", placeholder="Tu contraseña", password=True
        ),
    }


__all__ = ["campos_login"]
