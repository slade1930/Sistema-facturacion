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
from app.api.v1.endpoints.ml import anomalias as anomalias_api
from app.api.v1.endpoints.ml import asistente as asistente_api
from app.api.v1.endpoints.ml import pronostico as pronostico_api
from app.api.v1.endpoints.ml import recomendaciones as recomendaciones_api

router = APIRouter()

router.include_router(facturas.router)
router.include_router(historial.router)
router.include_router(verificar.router)
router.include_router(pdf.router)
router.include_router(configuracion.router)
# Gente, este router va primero: /pedidos/por-facturar no debe chocar con /pedidos/{id}.
router.include_router(pedidos.router)
router.include_router(catalogo.router)
router.include_router(catalogo_api.router)
router.include_router(pedidos_b2b.router)
router.include_router(carrito.router)
router.include_router(asistente_api.router)
router.include_router(anomalias_api.router)
router.include_router(pronostico_api.router)
router.include_router(recomendaciones_api.router)
