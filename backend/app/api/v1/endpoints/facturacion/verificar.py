from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.repositories.facturacion import FacturaRepository
from app.schemas.facturacion import FacturaVerificacion
from app.services.verificacion import validar_codigo_verificacion

router = APIRouter(prefix="/verificar", tags=["Verificación"])


@router.get("/{numero_serie}/{codigo}", response_model=FacturaVerificacion)
def verificar_factura(numero_serie: str, codigo: str, db: Session = Depends(get_db)):
    factura = FacturaRepository.obtener_por_numero_serie(db, numero_serie)
    if factura is None or not validar_codigo_verificacion(
        codigo,
        factura.numero_serie,
        factura.total,
        factura.cliente_ruc or "",
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró una factura con ese número y código de verificación.",
        )

    return FacturaVerificacion(
        valida=True,
        numero_serie=factura.numero_serie,
        codigo_verificacion=factura.codigo_verificacion,
        fecha=factura.fecha,
        cliente_nombre=factura.cliente_nombre,
        total=factura.total,
        estado=factura.estado,
    )