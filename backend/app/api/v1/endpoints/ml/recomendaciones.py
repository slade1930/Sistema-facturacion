"""Recomendaciones (Módulo 3, endpoint: mdeh25-droid).

GET /ml/recomendaciones?producto_ids=1,2,3

Sugiere, no decide: si algo falla, responde con lista vacía y nunca con
un error 500. Mientras no exista un modelo entrenado, el resultado sale de
las reglas de asociación y de "más vendidos", y se marca "sin evaluar".
Equipo ML prepara, Equipo 4 registra: router.py lo edita Moisés.
"""
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import requiere_auth
from app.db.session import get_db
from app.ml.features.recomendaciones import cestas_desde_dataset
from app.ml.reglas.recomendaciones import recomendaciones_por_reglas
from app.models.catalogo import LineaPedidoB2B, PedidoB2B, Producto
from app.models.facturacion import Factura, LineaFactura

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ml/recomendaciones",
    tags=["ml"],
    dependencies=[Depends(requiere_auth)],
)

MAX_IDS = 50


def _error(status: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "code": code})


def _parsear_ids(texto: str) -> list[int]:
    """'1,2,3' -> [1, 2, 3] sin repetidos. ValueError si el texto no sirve."""
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    if not partes or len(partes) > MAX_IDS:
        raise ValueError("cantidad de ids fuera de rango")
    ids: list[int] = []
    for parte in partes:
        valor = int(parte)
        if valor < 1:
            raise ValueError("id no positivo")
        if valor not in ids:
            ids.append(valor)
    return ids


def _valor(x):
    """Enum -> su valor de texto; cualquier otra cosa queda igual."""
    return getattr(x, "value", x)


def _fecha(x):
    return x.isoformat() if x is not None else None


def _facturas_como_dicts(db: Session) -> list[dict]:
    """Facturas y líneas como dicts, que es lo que espera features/recomendaciones.py.

    Los montos pasan a float porque es analítica del ML, no contabilidad.
    """
    lineas: dict[int, list[dict]] = {}
    filas = db.execute(
        select(
            LineaFactura.factura_id,
            LineaFactura.producto_id,
            LineaFactura.cantidad,
            LineaFactura.monto,
        ).where(LineaFactura.producto_id.is_not(None))
    )
    for factura_id, producto_id, cantidad, monto in filas:
        lineas.setdefault(factura_id, []).append(
            {"producto_id": producto_id, "cantidad": float(cantidad), "monto": float(monto)}
        )
    facturas = db.execute(
        select(
            Factura.id,
            Factura.estado,
            Factura.cliente_ruc,
            Factura.cliente_nombre,
            Factura.fecha,
        )
    )
    return [
        {
            "id": fid,
            "estado": _valor(estado),
            "cliente_ruc": ruc,
            "cliente_nombre": nombre,
            "fecha": _fecha(fecha),
            "lineas": lineas.get(fid, []),
        }
        for fid, estado, ruc, nombre, fecha in facturas
    ]


def _pedidos_como_dicts(db: Session) -> list[dict]:
    lineas: dict[int, list[dict]] = {}
    filas = db.execute(
        select(
            LineaPedidoB2B.pedido_id,
            LineaPedidoB2B.producto_id,
            LineaPedidoB2B.cantidad,
            LineaPedidoB2B.subtotal,
        )
    )
    for pedido_id, producto_id, cantidad, subtotal in filas:
        lineas.setdefault(pedido_id, []).append(
            {"producto_id": producto_id, "cantidad": float(cantidad), "subtotal": float(subtotal)}
        )
    pedidos = db.execute(
        select(
            PedidoB2B.id,
            PedidoB2B.estado,
            PedidoB2B.cliente_id,
            PedidoB2B.fecha_creacion,
        )
    )
    return [
        {
            "id": pid,
            "estado": _valor(estado),
            "cliente_id": cliente_id,
            "fecha_creacion": _fecha(fecha),
            "lineas": lineas.get(pid, []),
        }
        for pid, estado, cliente_id, fecha in pedidos
    ]


@router.get("")
def recomendar(
    producto_ids: str = Query(..., description="Ids del carrito separados por coma, ej. 1,2,3"),
    n: int = Query(5, ge=1, le=20, description="Cuántas recomendaciones devolver"),
    db: Session = Depends(get_db),
):
    try:
        carrito = _parsear_ids(producto_ids)
    except ValueError:
        return _error(
            400,
            "producto_ids debe ser una lista de enteros positivos separados por coma",
            "producto_ids_invalidos",
        )

    try:
        inactivos = set(
            db.scalars(select(Producto.id).where(Producto.estado_activo.is_(False))).all()
        )
        cestas = cestas_desde_dataset(
            facturas=_facturas_como_dicts(db),
            pedidos=_pedidos_como_dicts(db),
        )
        resultado = recomendaciones_por_reglas(cestas, carrito, n=n, excluir=inactivos)
    except Exception:  # el ML sugiere y nunca bloquea
        logger.exception("Fallo al generar recomendaciones; se responde sin sugerencias")
        resultado = []

    # Cuando makirvy tenga el autoencoder entrenado, aquí se carga con
    # cargar_modelo("recomendaciones") y se cambia evaluado/modelo.
    return {"evaluado": False, "modelo": "sin evaluar", "resultado": resultado}