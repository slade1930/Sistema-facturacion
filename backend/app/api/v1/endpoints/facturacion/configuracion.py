
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import requiere_auth
from app.db.session import get_db
from app.repositories.facturacion import ConfiguracionNegocioRepository
from app.schemas.facturacion import (
    ConfiguracionNegocioRead,
    ConfiguracionNegocioUpdate,
)

router = APIRouter(
    prefix="/configuracion",
    tags=["Configuración"],
    dependencies=[Depends(requiere_auth)],
)


@router.get("", response_model=ConfiguracionNegocioRead)
def obtener_configuracion(
    db: Session = Depends(get_db),
):
    configuracion = ConfiguracionNegocioRepository.obtener(db)

    if configuracion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La configuración del negocio no existe.",
        )

    return configuracion


@router.put("", response_model=ConfiguracionNegocioRead)
def actualizar_configuracion(
    datos: ConfiguracionNegocioUpdate,
    db: Session = Depends(get_db),
):
    try:
        configuracion = ConfiguracionNegocioRepository.guardar_o_actualizar(
            db,
            datos,
            commit=False,
        )

        db.commit()
        db.refresh(configuracion)

        return configuracion

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
