
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.deps import requiere_admin, requiere_auth
from app.db.session import get_db
from app.repositories.facturacion import ConfiguracionNegocioRepository
from app.utils.storage import borrar_logo, guardar_logo
from app.schemas.facturacion import (
    ConfiguracionNegocioRead,
    ConfiguracionNegocioUpdate,
)

router = APIRouter(
    prefix="/configuracion",
    tags=["Configuración"],
    dependencies=[Depends(requiere_auth), Depends(requiere_admin)],
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
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/logo", response_model=ConfiguracionNegocioRead)
async def subir_logo(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contenido = await archivo.read()

    try:
        ruta_relativa = guardar_logo(
            contenido,
            archivo.filename or "",
            archivo.content_type or "",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    configuracion = ConfiguracionNegocioRepository.obtener(db)

    if configuracion is None:
        borrar_logo(ruta_relativa)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La configuración del negocio no existe.",
        )

    logo_anterior = configuracion.logo
    configuracion.logo = ruta_relativa

    try:
        # Gente, el commit va acá nomás: el repo sigue sin encargarse de eso.
        db.commit()
        db.refresh(configuracion)
    except Exception:
        db.rollback()
        borrar_logo(ruta_relativa)
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar el logo.",
        )

    if logo_anterior != ruta_relativa:
        try:
            borrar_logo(logo_anterior)
        except OSError:
            # Gente, si el viejo no se puede borrar, no rompemos la respuesta.
            pass

    return configuracion
