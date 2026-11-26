from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.core.config import validar_api_key, validar_factura_hmac_key
from app.core.logging import configurar_logging
from app.db.session import engine
from app.repositories.catalogo import IntegridadError
from app.services.ciclo_vida import FacturaYaAnuladaError

# Gente, una sola vez al arrancar; el guard interno no duplica handlers.
configurar_logging()
validar_api_key()
validar_factura_hmac_key()

app = FastAPI(title="Sistema de facturación")
app.include_router(api_v1_router, prefix="/api/v1")


@app.exception_handler(IntegridadError)
@app.exception_handler(FacturaYaAnuladaError)
def conflicto(request: Request, exc: Exception):
    return JSONResponse(
        status_code=409,
        content={"detalle": str(exc)},
    )


@app.exception_handler(ValueError)
def valor_invalido(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"detalle": str(exc)},
    )


@app.exception_handler(LookupError)
def no_encontrado(request: Request, exc: LookupError):
    return JSONResponse(
        status_code=404,
        content={"detalle": str(exc) or "No encontrado."},
    )


@app.get("/health")
def health():
    # Hacemos un SELECT 1 para saber que la base responde, no solo el proceso.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
