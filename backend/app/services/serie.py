"""Numeración consecutiva por año de facturas (FAC) y órdenes de compra (OC).

Cada serie tiene su propio contador (ContadorSerie y ContadorOrdenCompra),
así que los números de factura y de OC nunca se mezclan.

Solo hace flush(), nunca commit: el número queda reservado dentro de la
transacción del documento y se libera si la factura/pedido hace rollback.

PUNTOS DE COORDINACIÓN PENDIENTES (no resolver aquí, avisar al equipo):
1. Validadores: existe app/services/Validators.py (implementado) y el
   placeholder vacío app/utils/validators.py. Confirmar cuál es la ruta
   oficial para que ningún import se rompa si renombran/mueven el módulo.
2. Duplicidad: el equipo de catálogo tiene ContadorSerieRepository
   (repositories/facturacion.py) con su propio SELECT ... FOR UPDATE.
   Este servicio usa upsert ON CONFLICT DO NOTHING + FOR UPDATE, que es
   atómico aunque el contador del año no exista todavía. Definir con los
   líderes cuál implementación usan los endpoints (ideal: que el repo
   delegue aquí).
3. codigo_verificacion: Factura.codigo_verificacion es String(12)
   obligatorio y NO unique. Este servicio solo genera numero_serie;
   la generación del código (HMAC u otra regla) queda pendiente con el
   compañero de seguridad/reglas y el equipo de api.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.catalogo import ContadorOrdenCompra
from app.models.facturacion import ContadorSerie

PREFIJO_FACTURA = "FAC"
PREFIJO_ORDEN_COMPRA = "OC"


def _formato(prefijo: str, anio: int, numero: int) -> str:
    """Devuelve el folio, por ejemplo FAC-2026-0001."""
    return f"{prefijo}-{anio}-{numero:04d}"


def _siguiente(db: Session, modelo, prefijo: str, anio: int) -> str:
    # 1) Crea el contador del año si no existe. ON CONFLICT DO NOTHING evita
    #    errores si dos procesos lo intentan crear al mismo tiempo.
    db.execute(
        insert(modelo)
        .values(anio=anio, ultimo_numero=0)
        .on_conflict_do_nothing(index_elements=["anio"])
    )
    # 2) Bloquea la fila hasta el final de la transacción (FOR UPDATE):
    #    nadie más puede tomar el mismo número mientras tanto.
    fila = db.execute(
        select(modelo).where(modelo.anio == anio).with_for_update()
    ).scalar_one()
    # 3) Incrementa y devuelve el folio.
    fila.ultimo_numero += 1
    db.flush()
    return _formato(prefijo, anio, fila.ultimo_numero)


def siguiente_numero_factura(db: Session, anio: int) -> str:
    """Siguiente número de factura del año: FAC-AAAA-0001."""
    return _siguiente(db, ContadorSerie, PREFIJO_FACTURA, anio)


def siguiente_numero_oc(db: Session, anio: int) -> str:
    """Siguiente número de orden de compra del año: OC-AAAA-0001."""
    return _siguiente(db, ContadorOrdenCompra, PREFIJO_ORDEN_COMPRA, anio)
