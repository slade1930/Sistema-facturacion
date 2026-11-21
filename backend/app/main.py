from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine

app = FastAPI(title="Sistema de facturación")


@app.get("/health")
def health():
    # Hacemos un SELECT 1 para saber que la base responde, no solo el proceso.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
