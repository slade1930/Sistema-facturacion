from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor, get_db, requiere_auth
from app.core.constants import MEDIA_TYPE_PDF
from app.repositories.facturacion import ConfiguracionNegocioRepository
from app.services.aislamiento import factura_visible
from app.services.pdf import construir_datos_comprobante, generar_pdf

router = APIRouter(
    prefix="/facturas",
    tags=["PDF"],
    dependencies=[Depends(requiere_auth)],
)


@router.get("/{factura_id}/pdf")
def descargar_pdf(
    factura_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    factura = factura_visible(db, actor, factura_id)
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