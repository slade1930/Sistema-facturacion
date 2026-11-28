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
    SectorEmpresa,
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
from .inventario import Inventario, MovimientoInventario, TipoMovimiento
from .seguridad import Auditoria, Cuenta, RolCuenta, Sesion

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
    "SectorEmpresa",
    "RolCuenta",
    "Cuenta",
    "Sesion",
    "Auditoria",
    "Inventario",
    "MovimientoInventario",
    "TipoMovimiento",
]
