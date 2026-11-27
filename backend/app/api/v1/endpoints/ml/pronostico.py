"""Sugerencias de pronóstico (Módulo 2).

Módulo app.api.v1.endpoints.ml. Equipo ML prepara, Equipo 4 registra
(router.py todavía no lo incluye). Sugiere, no decide: sin modelo
entrenado responde {"evaluado": false, ...} y nunca bloquea.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_auth
from app.ml.inferencia import cargador
from app.ml.modelos import pronostico as modelo_clasico
from app.ml.modelos import pronostico_lstm
from app.models.facturacion import EstadoFactura, Factura, LineaFactura

router = APIRouter(
    prefix="/ml/pronostico",
    tags=["ml"],
    dependencies=[Depends(requiere_auth)],
)

NOMBRES_MODELOS = ("pronostico_lstm.pt", "pronostico_clasico.joblib")


def _cargar_mejor_modelo():
    """Devuelve (nombre, artefacto) del primer modelo disponible o (None, None)."""
    for nombre in NOMBRES_MODELOS:
        artefacto = cargador.cargar_artefacto(nombre)
        if artefacto is not None:
            return nombre, artefacto
    return None, None


def _predecir(artefacto, horizonte):
    tipo = artefacto.get("tipo") if isinstance(artefacto, dict) else None
    if tipo == "lstm":
        return pronostico_lstm.predecir(artefacto, horizonte=horizonte)
    return modelo_clasico.predecir(artefacto, horizonte=horizonte)


def _ventana_minima(artefacto):
    if isinstance(artefacto, dict) and artefacto.get("tipo") == "lstm":
        return int(artefacto.get("ventana", pronostico_lstm.VENTANA))
    return 14  # estacionalidad 12 + 2, mismo mínimo del clásico


def _serie_desde_db(db: Session, producto_id: int | None = None):
    """Serie mensual (periodos, valores) desde facturas emitidas."""
    if producto_id is None:
        filas = db.execute(
            select(Factura.fecha, Factura.total).where(
                Factura.estado != EstadoFactura.ANULADA
            )
        ).all()
        acum = {}
        for fecha, total in filas:
            clave = fecha.strftime("%Y-%m")
            acum[clave] = acum.get(clave, 0.0) + float(total or 0)
    else:
        filas = db.execute(
            select(Factura.fecha, LineaFactura.monto)
            .join(LineaFactura, LineaFactura.factura_id == Factura.id)
            .where(
                Factura.estado != EstadoFactura.ANULADA,
                LineaFactura.producto_id == producto_id,
            )
        ).all()
        acum = {}
        for fecha, monto in filas:
            clave = fecha.strftime("%Y-%m")
            acum[clave] = acum.get(clave, 0.0) + float(monto or 0)
    periodos = sorted(acum)
    return periodos, [round(acum[p], 2) for p in periodos]


def _siguientes_periodos(ultimo: str, n: int) -> list[str]:
    """Los n 'YYYY-MM' posteriores a `ultimo`, sin dependencias."""
    anio, mes = (int(parte) for parte in ultimo.split("-"))
    salida = []
    for _ in range(n):
        mes += 1
        if mes > 12:
            mes, anio = 1, anio + 1
        salida.append(f"{anio:04d}-{mes:02d}")
    return salida


@router.get("")
def obtener_pronostico(
    meses: int = Query(6, ge=1, le=24),
    producto_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    nombre, artefacto = _cargar_mejor_modelo()
    if artefacto is None:
        return {"evaluado": False, "modelo": None, "resultado": None}

    periodos, serie = _serie_desde_db(db, producto_id)
    pred = _predecir(artefacto, meses)
    if pred is None:
        return {
            "evaluado": False,
            "modelo": nombre,
            "resultado": {
                "estado": "sin evaluar",
                "motivo": "sin predicción",
            },
        }
    if len(serie) < _ventana_minima(artefacto):
        return {
            "evaluado": False,
            "modelo": nombre,
            "resultado": {
                "estado": "sin evaluar",
                "motivo": "datos insuficientes",
            },
        }

    futuro = _siguientes_periodos(periodos[-1], len(pred))
    return {
        "evaluado": True,
        "modelo": nombre,
        "resultado": {
            "nivel": "producto" if producto_id is not None else "total",
            "producto_id": producto_id,
            "periodos": futuro,
            "valores": [round(float(v), 2) for v in pred],
            "horizonte": meses,
        },
    }
