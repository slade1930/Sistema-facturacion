from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_auth
from app.models.catalogo import TipoEmpaque
from app.repositories.catalogo import ProductoRepository
from app.schemas.carrito import (
    CarritoCalcularRequest,
    CarritoCalcularResponse,
    CarritoLineaCalculo,
)
from app.services.pedidos import precio_de_presentacion, subtotal_linea
from app.services.totales import calcular_totales

router = APIRouter(
    prefix="/carrito",
    tags=["Carrito"],
    dependencies=[Depends(requiere_auth)],
)


def _linea_para_totales(
    producto, item, presentacion: TipoEmpaque, precio: Decimal
) -> dict:
    """Arma el dict que espera services.totales con la misma lógica de facturar_pedido_b2b."""
    es_caja = presentacion == TipoEmpaque.CAJA
    es_media_caja = presentacion == TipoEmpaque.MEDIA_CAJA
    return {
        "cantidad": item.cantidad,
        "precio_unitario": precio,
        "precio_unidad": None if (es_caja or es_media_caja) else producto.precio_unidad,
        "descuento_pct": Decimal("0.00"),
        "gravada": producto.aplica_itbms,
        "cobrar_por": "caja" if es_caja else "unidad",
    }


@router.post("/calcular", response_model=CarritoCalcularResponse)
def calcular_carrito(datos: CarritoCalcularRequest, db: Session = Depends(get_db)):
    repo = ProductoRepository(db)
    lineas_calculo = []
    lineas_totales = []

    for item in datos.lineas:
        producto = repo.get(item.producto_id)
        if producto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto no encontrado: {item.producto_id}.",
            )
        if not producto.estado_activo:
            raise HTTPException(
                status_code=422,
                detail=f"El producto '{producto.nombre}' no está activo.",
            )
        try:
            precio = precio_de_presentacion(producto, item.tipo_empaque)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        lineas_totales.append(
            _linea_para_totales(producto, item, item.tipo_empaque, precio)
        )
        lineas_calculo.append(
            CarritoLineaCalculo(
                producto_id=producto.id,
                descripcion=producto.nombre,
                tipo_empaque=item.tipo_empaque,
                cantidad=item.cantidad,
                precio_unitario=precio,
                subtotal=subtotal_linea(precio, item.cantidad),
            )
        )

    totales = calcular_totales(lineas_totales, portes=Decimal("0.00"))

    return CarritoCalcularResponse(
        lineas=lineas_calculo,
        **totales,
    )
