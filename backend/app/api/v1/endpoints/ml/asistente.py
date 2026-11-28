"""Sugerencias del asistente (paso 0; se arma en el paso 4).

Módulo app.api.v1.endpoints.ml. Equipo ML prepara, Equipo 4 registra.
Sugiere, no decide: router.py todavía no lo incluye.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_admin, requiere_auth
from app.ml.asistente import catalogo, intenciones
from app.ml.modelos import asistente as modelo

router = APIRouter(
    prefix="/ml/asistente",
    tags=["ml"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
)

NOMBRE_LINEA_BASE = "linea-base-palabras-clave"
NO_ENTENDI = "No entendí la pregunta. Probá con ventas por mes, por cliente o por producto."


class ConsultaAsistente(BaseModel):
    pregunta: str


def _sin_respuesta(evaluado, nombre_modelo):
    return {
        "evaluado": evaluado,
        "modelo": nombre_modelo,
        "resultado": {
            "intencion": None,
            "confianza": None,
            "respuesta": NO_ENTENDI,
            "datos": [],
        },
    }


@router.post("/consultar")
def consultar(datos: ConsultaAsistente, db: Session = Depends(get_db)):
    pregunta = (datos.pregunta or "").strip()
    if not pregunta:
        raise HTTPException(
            status_code=422,
            detail="La pregunta no puede estar vacía.",
        )

    hoy = date.today()
    prediccion = modelo.predecir(pregunta, hoy=hoy)
    evaluado = prediccion is not None
    nombre_modelo = modelo.NOMBRE_PUBLICO if evaluado else NOMBRE_LINEA_BASE
    clasificacion = prediccion or intenciones.clasificar(pregunta, hoy=hoy)

    if clasificacion is None or clasificacion.nombre not in catalogo.CATALOGO:
        return _sin_respuesta(evaluado, nombre_modelo)

    consulta = catalogo.CATALOGO[clasificacion.nombre]
    try:
        respuesta = consulta(db, hoy=hoy, **clasificacion.parametros)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "evaluado": evaluado,
        "modelo": nombre_modelo,
        "resultado": {
            "intencion": clasificacion.nombre,
            "confianza": round(clasificacion.confianza, 4),
            **respuesta,
        },
    }
