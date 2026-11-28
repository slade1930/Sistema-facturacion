"""Valores fijos del panel de administración; etapa C2."""

from datetime import date, timedelta
from typing import Any

SECTORES_ADMIN = {
    "tecnologia": "Tecnología",
    "turismo": "Turismo",
    "supermercado": "Supermercado",
}

ESTADOS_PEDIDO_ADMIN = {
    "pendiente": "Pendiente",
    "en_proceso": "En proceso",
    "facturado": "Facturado",
    "cancelado": "Cancelado",
}

TIPOS_MOVIMIENTO_ADMIN = {
    "entrada": "Entrada",
    "salida": "Salida",
    "ajuste": "Ajuste",
}

OPCIONES_ESTADO = {
    "": "Todos",
    "true": "Solo activos",
    "false": "Solo inactivos",
}

OPCIONES_STOCK = {
    "": "Todo el inventario",
    "con": "Con existencias",
    "bajo": "Bajo el mínimo",
    "sin": "Sin existencias",
}


def rango_periodo(clave: str) -> tuple[Any, Any]:
    """Convierte el período elegido en fechas para el backend; sin cálculos de negocio."""
    hoy = date.today()
    if clave == "30":
        return hoy - timedelta(days=30), hoy
    if clave == "90":
        return hoy - timedelta(days=90), hoy
    if clave == "anio":
        return date(hoy.year, 1, 1), hoy
    return None, None


__all__ = [
    "ESTADOS_PEDIDO_ADMIN",
    "OPCIONES_ESTADO",
    "OPCIONES_STOCK",
    "SECTORES_ADMIN",
    "TIPOS_MOVIMIENTO_ADMIN",
    "rango_periodo",
]
