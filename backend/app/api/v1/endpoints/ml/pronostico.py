"""Sugerencias de pronóstico (paso 0; se arma en el paso 4).

Módulo app.api.v1.endpoints.ml. Equipo ML prepara, Equipo 4 registra.
Sugiere, no decide: router.py todavía no lo incluye.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/ml/pronostico", tags=["ml"])
