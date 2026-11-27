from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_auth
from app.core.constants import MEDIA_TYPE_PDF
from app.repositories.facturacion import (
    ConfiguracionNegocioRepository,
    FacturaRepository,
)
from app.services.pdf import construir_datos_comprobante, generar_pdf

router = APIRouter(
    prefix="/facturas",
    tags=["PDF"],
    dependencies=[Depends(requiere_auth)],
)


@router.get("/{factura_id}/pdf")
def descargar_pdf(factura_id: int, db: Session = Depends(get_db)):
    factura = FacturaRepository.obtener_por_id(db, factura_id)
    if factura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada.",
        )

    configuracion = ConfiguracionNegocioRepository.obtener(db)
    datos = construir_datos_comprobante(factura, configuracion=configuracion)
    contenido = generar_pdf(datos)

    return Response(
        content=contenido,
        media_type=MEDIA_TYPE_PDF,
        headers={
            "Content-Disposition": f'inline; filename="factura-{factura.numero_serie}.pdf"'
        },
    )