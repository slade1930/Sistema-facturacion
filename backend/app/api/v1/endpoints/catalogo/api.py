from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import Actor, get_actor, requiere_auth
from app.db.session import get_db
from app.repositories.catalogo import CategoriaRepository, ProductoRepository
from app.schemas.catalogo import CategoriaRead, ProductoRead

router = APIRouter(
    prefix="/catalogo",
    tags=["Catálogo"],
    dependencies=[Depends(requiere_auth)],
)


@router.get("/buscar")
def buscar_catalogo(
    q: str = Query(
        ...,
        min_length=1,
        description="Texto que se desea buscar",
    ),
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
):
    sector = actor.sector if actor.es_empresa else None
    productos = ProductoRepository(db).listar(
        busqueda=q,
        solo_activos=True,
        skip=0,
        limit=limite,
        sector=sector,
    )

    categorias = CategoriaRepository(db).listar(
        busqueda=q,
        skip=0,
        limit=limite,
        sector=sector,
    )

    return {
        "consulta": q,
        "productos": [
            ProductoRead.model_validate(producto).model_dump(mode="json")
            for producto in productos
        ],
        "categorias": [
            CategoriaRead.model_validate(categoria).model_dump(mode="json")
            for categoria in categorias
        ],
    }
