"""Registro unico de modelos para que Alembic vea todas las tablas."""

# Gente, importamos los dos archivos para que Alembic siga viendo las 10 tablas.

from .catalogo import (
    Categoria,
    ClienteB2B,
    ContadorOrdenCompra,
    EstadoPedido,
    LineaPedidoB2B,
    PedidoB2B,
    Producto,
    TipoEmpaque,
)
from .facturacion import (
    CobrarPor,
    CondicionPago,
    ConfiguracionNegocio,
    ContadorSerie,
    EstadoFactura,
    Factura,
    LineaFactura,
)

__all__ = [
    "Categoria",
    "ClienteB2B",
    "CobrarPor",
    "CondicionPago",
    "ConfiguracionNegocio",
    "ContadorOrdenCompra",
    "ContadorSerie",
    "EstadoFactura",
    "EstadoPedido",
    "Factura",
    "LineaFactura",
    "LineaPedidoB2B",
    "PedidoB2B",
    "Producto",
    "TipoEmpaque",
]
