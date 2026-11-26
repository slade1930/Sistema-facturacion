from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, requiere_auth
from app.models.facturacion import Factura, LineaFactura
from app.repositories.facturacion import ContadorSerieRepository, FacturaRepository
from app.schemas.facturacion import FacturaCreate, FacturaRead, LineaFacturaCreate
from app.services.ciclo_vida import duplicar_factura
from app.services.totales import aplicar_totales
from app.services.verificacion import generar_codigo_verificacion

router = APIRouter(
    prefix="/facturas",
    tags=["Facturas"],
    dependencies=[Depends(requiere_auth)],
)


def _linea_nueva(datos: LineaFacturaCreate) -> LineaFactura:
    return LineaFactura(
        orden=datos.orden,
        descripcion=datos.descripcion,
        codigo_barras=datos.codigo_barras,
        categoria=datos.categoria,
        cantidad=datos.cantidad,
        precio_unitario=datos.precio_unitario,
        precio_unidad=datos.precio_unidad,
        descuento_pct=datos.descuento_pct,
        gravada=datos.gravada,
        unidades_por_caja=datos.unidades_por_caja,
        cobrar_por=datos.cobrar_por,
        monto=None,
        producto_id=datos.producto_id,
    )


def _obtener_o_404(db: Session, factura_id: int) -> Factura:
    factura = FacturaRepository.obtener_por_id(db, factura_id)
    if factura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada.",
        )
    return factura


@router.post("", response_model=FacturaRead, status_code=status.HTTP_201_CREATED)
def crear_factura(datos: FacturaCreate, db: Session = Depends(get_db)):
    fecha = datos.fecha or date.today()
    numero_serie = ContadorSerieRepository.obtener_siguiente_numero(db, fecha.year)
    lineas = [_linea_nueva(linea) for linea in datos.lineas]

    valores = datos.model_dump(exclude={"lineas"})
    valores.update(
        {
            "fecha": fecha,
            "numero_serie": numero_serie,
            "codigo_verificacion": "",
        }
    )
    factura = Factura(**valores, lineas=lineas)

    aplicar_totales(factura)
    factura.codigo_verificacion = generar_codigo_verificacion(
        factura.numero_serie,
        factura.total,
        factura.cliente_ruc or "",
    )

    FacturaRepository.crear(db, factura, lineas, commit=False)
    db.commit()
    db.refresh(factura)
    return factura


@router.get("/{factura_id}", response_model=FacturaRead)
def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    return _obtener_o_404(db, factura_id)


@router.post("/{factura_id}/anular", response_model=FacturaRead)
def anular_factura(factura_id: int, db: Session = Depends(get_db)):
    factura = _obtener_o_404(db, factura_id)
    FacturaRepository.anular(db, factura, commit=False)
    db.commit()
    db.refresh(factura)
    return factura


@router.post(
    "/{factura_id}/duplicar",
    response_model=FacturaRead,
    status_code=status.HTTP_201_CREATED,
)
def duplicar_factura_endpoint(factura_id: int, db: Session = Depends(get_db)):
    factura = _obtener_o_404(db, factura_id)
    nueva = duplicar_factura(db, factura)
    db.commit()
    db.refresh(nueva)
    return nueva
