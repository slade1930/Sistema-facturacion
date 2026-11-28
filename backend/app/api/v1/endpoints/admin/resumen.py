"""Resumen global para administración. Rol admin; etapa A."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_admin, requiere_auth
from app.models.catalogo import PedidoB2B
from app.models.facturacion import Factura
from app.models.inventario import Inventario
from app.models.seguridad import Cuenta

router = APIRouter(
    prefix="/admin",
    tags=["Administración"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
)


@router.get("/resumen")
def resumen_admin(db: Session = Depends(get_db)) -> dict:
    """Totales globales; la interfaz de empresa usará solo rutas de su token."""
    total_facturas, total_facturado = db.execute(
        select(func.count(Factura.id), func.coalesce(func.sum(Factura.total), 0))
    ).one()
    total_empresas = db.scalar(
        select(func.count(Cuenta.id)).where(Cuenta.rol == "empresa")
    )
    total_pedidos = db.scalar(select(func.count(PedidoB2B.id)))
    productos_bajo_stock = db.scalar(
        select(func.count(Inventario.producto_id)).where(
            Inventario.existencias < Inventario.stock_minimo
        )
    )
    return {
        "generado_en": datetime.now(timezone.utc),
        "total_empresas": total_empresas,
        "total_pedidos": total_pedidos,
        "total_facturas": total_facturas,
        "total_facturado": total_facturado,
        "productos_bajo_stock": productos_bajo_stock,
    }
