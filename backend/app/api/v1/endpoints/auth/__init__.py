"""Rutas públicas de acceso al portal. Empresa y admin; etapa A."""

from fastapi import APIRouter

from . import login, registro, sesion

router = APIRouter()
router.include_router(login.router)
router.include_router(registro.router)
router.include_router(sesion.router)

__all__ = ["router"]
