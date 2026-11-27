from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.core.config import validar_api_key, validar_factura_hmac_key
from app.core.errors import registrar_manejadores
from app.core.logging import configurar_logging
from app.db.session import engine

# Gente, una sola vez al arrancar; el guard interno no duplica handlers.
configurar_logging()
validar_api_key()
validar_factura_hmac_key()

app = FastAPI(title="Sistema de facturación")
# Errores con un solo formato: {"detail": "...", "code": "..."}
registrar_manejadores(app)
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
def health():
    # Hacemos un SELECT 1 para saber que la base responde, no solo el proceso.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}