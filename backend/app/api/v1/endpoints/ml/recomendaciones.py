"""Sugerencias de recomendaciones (Módulo 3).

Usa el autoencoder si hay artefacto; si no, cae a las reglas de
asociación y finalmente a "más vendidos". El ML solo sugiere: no
modifica la base de datos, ignora productos inactivos y nunca
recomienda lo que ya está en el carrito.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    Actor,
    get_actor,
    get_db,
    requiere_auth,
    requiere_empresa_o_admin,
)
from app.ml.features.recomendaciones import cestas_desde_dataset
from app.ml.inferencia import cargador
from app.ml.modelos import recomendaciones as modelo_autoencoder
from app.ml.reglas.recomendaciones import recomendaciones_por_reglas
from app.repositories.catalogo import ProductoRepository
from app.repositories.facturacion import FacturaRepository
from app.repositories.pedidos import PedidoB2BRepository

router = APIRouter(
    prefix="/ml/recomendaciones",
    tags=["ml"],
)


@router.get(
    "",
    dependencies=[Depends(requiere_auth), Depends(requiere_empresa_o_admin)],
)
def ruta_recomendaciones(
    producto_ids: str = Query(
        default="",
        description="Ids del carrito separados por coma; se excluyen de la sugerencia.",
    ),
    n: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
) -> dict:
    """Entrada HTTP de `/ml/recomendaciones`."""
    ids = []
    for parte in producto_ids.split(","):
        parte = parte.strip()
        if parte.isdigit():
            ids.append(int(parte))
    return get_recomendaciones(
        producto_ids=ids,
        n=n,
        db=db,
        sector=actor.sector if actor.es_empresa else None,
        cliente_id=actor.cliente_id if actor.es_empresa else None,
    )

NOMBRE_MODELO = modelo_autoencoder.NOMBRE_MODELO
ARCHIVO_MODELO = modelo_autoencoder.ARCHIVO_MODELO

# Límites para no traer toda la tabla en cada petición.
MAX_TRANSACCIONES = 500
MAX_PRODUCTOS = 500


def _valor(objeto, campo, defecto=None):
    valor = getattr(objeto, campo, defecto)
    # Los enums str de SQLAlchemy se convierten solos con str(); las
    # fechas y los decimales se dejan como están para las features.
    return valor.value if hasattr(valor, "value") else valor


def _linea_dict(linea):
    return {
        "producto_id": getattr(linea, "producto_id", None),
        "cantidad": _valor(linea, "cantidad", 0),
        "monto": _valor(linea, "monto", 0),
        "subtotal": _valor(linea, "subtotal", 0),
    }


def _factura_dict(factura):
    return {
        "id": factura.id,
        "estado": _valor(factura, "estado", ""),
        "fecha": _valor(factura, "fecha"),
        "cliente_ruc": getattr(factura, "cliente_ruc", None),
        "cliente_nombre": getattr(factura, "cliente_nombre", None),
        "lineas": [_linea_dict(linea) for linea in factura.lineas],
    }


def _pedido_dict(pedido):
    return {
        "id": pedido.id,
        "cliente_id": getattr(pedido, "cliente_id", None),
        "estado": _valor(pedido, "estado", ""),
        "fecha_creacion": _valor(pedido, "fecha_creacion"),
        "lineas": [_linea_dict(linea) for linea in pedido.lineas],
    }


def _cargar_modelo():
    """Artefacto del autoencoder o None. No lanza hacia el endpoint."""
    try:
        ruta = cargador.cargar_modelo(ARCHIVO_MODELO)
        if ruta is None:
            return None
        return modelo_autoencoder.cargar_modelo(ruta)
    except Exception:
        return None


def get_recomendaciones(
    producto_ids: list[int] | None = None,
    n: int = 5,
    db: Session | None = None,
    *,
    sector: str | None = None,
    cliente_id: int | None = None,
) -> dict:
    """Top-n de productos para sugerir al carrito actual.

    Responde siempre con el contrato del ML: `evaluado`, `modelo` y
    `resultado`. Sin historial devuelve una lista vacía sin romper.
    """
    carrito = sorted({int(pid) for pid in producto_ids or [] if int(pid) > 0})

    # Solo activos: un producto dado de baja nunca se recomienda.
    try:
        productos = ProductoRepository(db).listar(
            solo_activos=True, limit=MAX_PRODUCTOS
        )
        productos_activos = [int(producto.id) for producto in productos]
    except Exception:
        productos = []
        productos_activos = []
    activos = set(productos_activos)

    if sector is not None:
        # La empresa solo puede ver productos de su sector; las pruebas de ML
        # usan repositorios falsos sin el parámetro `sector`, por eso se filtra
        # acá y no se cambia la firma de `listar`.
        activos = {
            int(producto.id)
            for producto in productos
            if getattr(producto, "categoria", None) is not None
            and getattr(
                getattr(producto.categoria, "sector", None), "value",
                getattr(producto.categoria, "sector", None),
            ) == sector
        }

    try:
        facturas = FacturaRepository.listar(
            db, skip=0, limit=MAX_TRANSACCIONES
        )
        pedidos = PedidoB2BRepository(db).listar(skip=0, limit=MAX_TRANSACCIONES)
        if cliente_id is not None:
            facturas = [
                f for f in facturas if getattr(f, "cliente_id", None) == cliente_id
            ]
            pedidos = [
                p for p in pedidos if getattr(p, "cliente_id", None) == cliente_id
            ]
        cestas = cestas_desde_dataset(
            {
                "facturas": [_factura_dict(f) for f in facturas],
                "pedidos": [_pedido_dict(p) for p in pedidos],
            }
        )
    except Exception:
        # Sin base o sin historial, la app sigue respondiendo.
        cestas = None

    excluidos = list(carrito)
    if cestas is not None and not cestas.empty:
        disponibles = {
            int(pid) for pid in cestas["producto_id"].dropna().unique()
        }
        excluidos = sorted(set(excluidos) | (disponibles - activos))

    artefacto = _cargar_modelo()
    items = None
    nombre_modelo = None
    if artefacto is not None:
        # El artefacto puede venir del dataset sintético: sus ids no tienen
        # por qué existir en la base real. Todo producto del modelo que no
        # esté activo se excluye; si no queda ninguno, caemos a las reglas.
        ids_modelo = {int(pid) for pid in (artefacto.get("productos") or [])}
        excluidos_modelo = sorted(ids_modelo - activos)
        items = modelo_autoencoder.recomendar(
            artefacto,
            carrito,
            n=n,
            excluir=sorted(set(excluidos) | set(excluidos_modelo)),
        )
        if items and all(item["producto_id"] in activos for item in items):
            nombre_modelo = NOMBRE_MODELO
        else:
            items = None

    if not items:
        try:
            items = recomendaciones_por_reglas(
                cestas,
                carrito,
                n=n,
                excluir=excluidos,
            )
        except Exception:
            items = []

    evaluado = bool(items) and all(
        activos and item["producto_id"] in activos for item in items
    )
    return {
        "evaluado": evaluado,
        "modelo": nombre_modelo,
        "resultado": {
            "producto_ids": carrito,
            "recomendaciones": items or [],
            "n": n,
        },
    }


# El alias se usa en el router principal y deja el nombre público corto.
recomendaciones_api = router
