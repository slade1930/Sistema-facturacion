"""Guardián de rol para las pantallas del administrador; etapa C2.

La sesión vive en `state.auth` (etapa B). Acá solo se consulta con importación
pereyosa: en la rama C2 ese módulo es un documento sin funciones y las pantallas
compartidas deben seguir funcionando. Al mezclar con `desarrollo`, las funciones
reales se usan solas y este guardián no duplica la sesión.
"""

from typing import Any

from nicegui import ui


async def conectar_sesion() -> None:
    """Habilita el almacenamiento de la pestaña cuando la etapa B está presente."""
    from state import auth

    conectar = getattr(auth, "conectar", None)
    if callable(conectar):
        await conectar()


def exigir_admin() -> bool:
    """Sigue solo con una sesión de administrador; si no, navega a otra página."""
    from state import auth

    obtener_token = getattr(auth, "token", None)
    obtener_datos = getattr(auth, "datos_usuario", None)
    if obtener_token is None or obtener_datos is None:
        # Stub de la etapa A: todavía no hay sesión que proteger.
        return True

    try:
        tiene_token = bool(obtener_token())
    except Exception:
        tiene_token = False
    if not tiene_token:
        ui.navigate.to("/login")
        return False

    try:
        datos: Any = obtener_datos() or {}
        rol = str(datos.get("rol") or "") if isinstance(datos, dict) else ""
    except Exception:
        rol = ""
    if rol != "admin":
        ui.navigate.to("/portal/inicio")
        return False
    return True


__all__ = ["conectar_sesion", "exigir_admin"]
