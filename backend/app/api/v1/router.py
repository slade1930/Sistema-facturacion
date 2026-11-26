from fastapi import APIRouter

from app.api.v1.endpoints.catalogo import api as catalogo_api
from app.api.v1.endpoints.catalogo import carrito, catalogo, pedidos_b2b
from app.api.v1.endpoints.facturacion import (
    configuracion,
    facturas,
    historial,
    pdf,
    pedidos,
    verificar,
)

router = APIRouter()

router.include_router(facturas.router)
router.include_router(historial.router)
router.include_router(verificar.router)
router.include_router(pdf.router)
router.include_router(configuracion.router)
router.include_router(pedidos.router)
router.include_router(catalogo.router)
router.include_router(catalogo_api.router)
router.include_router(pedidos_b2b.router)
router.include_router(carrito.router)
