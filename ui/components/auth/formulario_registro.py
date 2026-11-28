"""Campos del registro de empresa del portal; etapa B."""

from typing import Any

from components.auth.indicador_clave import indicador_clave
from components.forms import campo_orquidea, selector_orquidea
from state.auth import SECTORES


def campos_registro() -> dict[str, Any]:
    """Devuelve los campos necesarios para crear la cuenta de la empresa."""
    empresa = campo_orquidea("Nombre de la empresa")
    ruc = campo_orquidea("RUC")
    correo = campo_orquidea("Correo electrónico")
    direccion = campo_orquidea("Dirección")
    telefono = campo_orquidea("Teléfono")
    sucursal = campo_orquidea("Sucursal")
    sector = selector_orquidea("Sector", SECTORES)
    contrasena = campo_orquidea("Contraseña", password=True)
    indicador_clave(contrasena)
    return {
        "nombre_empresa": empresa,
        "ruc": ruc,
        "correo": correo,
        "direccion": direccion,
        "telefono": telefono,
        "sucursal": sucursal,
        "sector": sector,
        "contrasena": contrasena,
    }


__all__ = ["campos_registro"]
