"""Sugerencias de anomalías: el ML no decide el estado de la factura."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_admin, requiere_auth
from app.ml.modelos import anomalias as modelo
from app.models.facturacion import Factura
from app.repositories.facturacion import FacturaRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ml/anomalias",
    tags=["ml"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
)


class ResultadoAnomalia(BaseModel):
    factura_id: int
    puntaje_anomalia: Decimal | None = None
    en_revision: bool = False
    motivo_anomalia: str | None = None


class EvaluacionAnomalia(BaseModel):
    evaluado: bool
    modelo: str | None = None
    resultado: ResultadoAnomalia


def _puntaje_100(puntaje: float) -> Decimal:
    return Decimal(str(round(puntaje * 100, 2)))


def _motivo(prediccion) -> str:
    accion = "Sugiere revisión" if prediccion.en_revision else "No sugiere revisión"
    return (
        f"{accion}: Isolation Forest dio {_puntaje_100(prediccion.puntaje)}/100 "
        f"(umbral {_puntaje_100(modelo.UMBRAL_REVISION)}/100)."
    )


def _serie_repetida(db, factura: Factura) -> bool:
    """Best-effort: ¿ya existe otra factura con el mismo número de serie?"""
    numero = str(getattr(factura, "numero_serie", "") or "")
    if not numero:
        return False
    try:
        return FacturaRepository.existe_numero_serie(
            db, numero, excluir_id=getattr(factura, "id", None)
        )
    except Exception:
        # Sin base o con un DB de prueba: no bloqueamos la sugerencia.
        return False


def evaluar_en_memoria(factura: Factura, *, serie_repetida: bool = False):
    """Evalúa sin tocar el estado ni hacer commit; devuelve None sin modelo."""
    rasgos = modelo.desde_factura(factura, serie_repetida=serie_repetida)
    prediccion = modelo.predecir(rasgos)
    if prediccion is None:
        return None
    factura.en_revision = prediccion.en_revision
    factura.puntaje_anomalia = _puntaje_100(prediccion.puntaje)
    factura.motivo_anomalia = _motivo(prediccion)
    return prediccion


def evaluar_al_crear(factura: Factura, *, serie_repetida: bool = False) -> bool:
    """Hook best-effort para crear_factura: no hace commit ni bloquea."""
    try:
        return evaluar_en_memoria(
            factura, serie_repetida=serie_repetida
        ) is not None
    except Exception:
        logger.exception("No se pudo evaluar anomalías al crear la factura.")
        return False


@router.post("/evaluar/{factura_id}", response_model=EvaluacionAnomalia)
def evaluar_factura(factura_id: int, db: Session = Depends(get_db)):
    factura = FacturaRepository.obtener_por_id(db, factura_id)
    if factura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada.",
        )

    prediccion = evaluar_en_memoria(
        factura, serie_repetida=_serie_repetida(db, factura)
    )
    db.commit()
    db.refresh(factura)

    evaluado = prediccion is not None
    return EvaluacionAnomalia(
        evaluado=evaluado,
        modelo=modelo.NOMBRE_PUBLICO if evaluado else None,
        resultado=ResultadoAnomalia(
            factura_id=factura.id,
            puntaje_anomalia=factura.puntaje_anomalia if evaluado else None,
            en_revision=prediccion.en_revision if evaluado else False,
            motivo_anomalia=factura.motivo_anomalia if evaluado else None,
        ),
    )
