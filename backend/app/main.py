from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.core.cabeceras import CabecerasSeguridadMiddleware
from app.core.config import validar_api_key, validar_factura_hmac_key
from app.core.errors import registrar_manejadores
from app.core.logging import configurar_logging
from app.db.session import engine
from app.utils.storage import CARPETA_MEDIA

# Gente, una sola vez al arrancar; el guard interno no duplica handlers.
configurar_logging()
validar_api_key()
validar_factura_hmac_key()

app = FastAPI(title="Sistema de facturación")
app.add_middleware(CabecerasSeguridadMiddleware)
# Errores con un solo formato: {"detail": "...", "code": "..."}
registrar_manejadores(app)
app.include_router(api_v1_router, prefix="/api/v1")


def montar_media(aplicacion: FastAPI, directorio: Path | None = None) -> None:
    """Sirve los logos guardados en `backend/media/` sin exigir API key.

    El directorio se puede pasar en las pruebas para no tocar `media/` real.
    """
    base = Path(directorio) if directorio is not None else CARPETA_MEDIA
    base.mkdir(parents=True, exist_ok=True)
    aplicacion.mount("/media", StaticFiles(directory=base), name="media")


montar_media(app)


@app.get("/health")
def health():
    # Hacemos un SELECT 1 para saber que la base responde, no solo el proceso.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}