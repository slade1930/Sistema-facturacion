"""Componentes propios de las pantallas del administrador; etapa C2."""

from components.admin.api import cliente_admin
from components.admin.constantes import (
    ESTADOS_PEDIDO_ADMIN,
    OPCIONES_ESTADO,
    OPCIONES_STOCK,
    SECTORES_ADMIN,
    TIPOS_MOVIMIENTO_ADMIN,
    rango_periodo,
)
from components.admin.formato import dinero, fecha, numero, texto
from components.admin.graficos import grafico_grupos, grafico_ingresos
from components.admin.menu import SECCIONES_ADMIN, montar_admin
from components.admin.seguridad import conectar_sesion, exigir_admin
from components.admin.tablas import tabla_admin
from components.admin.tarjetas import tarjetas_admin

__all__ = [
    "ESTADOS_PEDIDO_ADMIN",
    "OPCIONES_ESTADO",
    "OPCIONES_STOCK",
    "SECCIONES_ADMIN",
    "SECTORES_ADMIN",
    "TIPOS_MOVIMIENTO_ADMIN",
    "cliente_admin",
    "conectar_sesion",
    "dinero",
    "exigir_admin",
    "fecha",
    "grafico_grupos",
    "grafico_ingresos",
    "montar_admin",
    "numero",
    "rango_periodo",
    "tabla_admin",
    "tarjetas_admin",
    "texto",
]
