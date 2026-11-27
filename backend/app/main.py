import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.core.config import validar_api_key, validar_factura_hmac_key
from app.core.errors import registrar_manejadores
from app.core.logging import configurar_logging
from app.db.session import engine

ORIGENES_UI = [
    origen.strip()
    for origen in os.getenv(
        "UI_ORIGIN",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origen.strip()
]

# Gente, una sola vez al arrancar; el guard interno no duplica handlers.
configurar_logging()
validar_api_key()
validar_factura_hmac_key()

app = FastAPI(title="Sistema de facturación")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_UI,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)
# Errores con un solo formato: {"detail": "...", "code": "..."}
registrar_manejadores(app)
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
def health():
    # Hacemos un SELECT 1 para saber que la base responde, no solo el proceso.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}