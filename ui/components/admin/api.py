"""Cliente de las llamadas de administración; etapa C2."""

from typing import Any


def cliente_admin() -> Any:
    """Usa el cliente con sesión de la etapa B si está disponible."""
    from state import auth

    crear = getattr(auth, "cliente_portal", None)
    if callable(crear):
        return crear()
    # Sin la etapa B no hay token: las pantallas siguen mostrando los datos
    # simulados y la integración final usa el cliente con sesión.
    from state.cliente_api import ClienteApi

    return ClienteApi()


__all__ = ["cliente_admin"]
