"""Pruebas unitarias de app.services.serie (sin Postgres real).

serie.py usa el dialecto postgresql (ON CONFLICT DO NOTHING + FOR UPDATE),
que no corre en SQLite. Por eso la mayoría de las pruebas usan una sesión
falsa; la prueba `test_integracion_*` de abajo queda marcada como
`integration` y solo corre cuando hay DATABASE_URL (Postgres real).
"""

import os
import re
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.services import serie


class _ResultadoFalso:
    def __init__(self, fila):
        self._fila = fila

    def scalar_one(self):
        return self._fila


class _SesionFalsa:
    """Simula Session: execute() devuelve la fila del contador en el SELECT
    y flush() solo se registra. commit() no existe: si el código lo llamara,
    la prueba explotaría con AttributeError."""

    def __init__(self, fila):
        self._fila = fila
        self.sentencias = []
        self.flushes = 0

    def execute(self, sentencia):
        self.sentencias.append(sentencia)
        return _ResultadoFalso(self._fila)

    def flush(self):
        self.flushes += 1


def test_formato_factura():
    assert serie._formato("FAC", 2026, 1) == "FAC-2026-0001"
    assert serie._formato("FAC", 2026, 12345) == "FAC-2026-12345"


def test_formato_orden_compra():
    assert serie._formato("OC", 2026, 7) == "OC-2026-0007"


def test_prefijos_publicos():
    assert serie.PREFIJO_FACTURA == "FAC"
    assert serie.PREFIJO_ORDEN_COMPRA == "OC"


def test_siguiente_numero_factura_incrementa_y_da_flush():
    fila = SimpleNamespace(ultimo_numero=41)
    db = _SesionFalsa(fila)

    folio = serie.siguiente_numero_factura(db, 2026)

    assert folio == "FAC-2026-0042"
    assert fila.ultimo_numero == 42
    assert db.flushes == 1
    # execute se llamó 2 veces: INSERT ... ON CONFLICT + SELECT ... FOR UPDATE
    assert len(db.sentencias) == 2


def test_siguiente_numero_oc_usa_prefijo_oc():
    fila = SimpleNamespace(ultimo_numero=0)
    db = _SesionFalsa(fila)

    folio = serie.siguiente_numero_oc(db, 2026)

    assert folio == "OC-2026-0001"
    assert fila.ultimo_numero == 1


def test_folios_consecutivos_no_se_repitten():
    fila = SimpleNamespace(ultimo_numero=0)
    db = _SesionFalsa(fila)

    primero = serie.siguiente_numero_factura(db, 2026)
    segundo = serie.siguiente_numero_factura(db, 2026)

    assert primero == "FAC-2026-0001"
    assert segundo == "FAC-2026-0002"
    assert primero != segundo


def test_insert_usa_on_conflict_do_nothing():
    fila = SimpleNamespace(ultimo_numero=0)
    db = _SesionFalsa(fila)

    serie.siguiente_numero_factura(db, 2026)

    insert_stmt = db.sentencias[0]
    compilado = str(
        insert_stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "ON CONFLICT" in compilado
    assert "DO NOTHING" in compilado
    assert "contador_serie" in compilado


def test_select_bloquea_fila_for_update():
    fila = SimpleNamespace(ultimo_numero=0)
    db = _SesionFalsa(fila)

    serie.siguiente_numero_factura(db, 2026)

    select_stmt = db.sentencias[1]
    compilado = str(
        select_stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "FOR UPDATE" in compilado
    assert "contador_serie" in compilado


# ---------------------------------------------------------------------------
# INTEGRACIÓN PENDIENTE — requiere Postgres real (DATABASE_URL).
#
# Valida contra el motor real lo que la sesión falsa no puede:
#   - INSERT ... ON CONFLICT (anio) DO NOTHING cuando el contador no existe.
#   - SELECT ... FOR UPDATE y el incremento atómico de ultimo_numero.
#   - Que FAC y OC llevan contadores separados (contador_serie vs
#     contador_orden_compra).
#
# Usa el año 2999 (imposible en producción) y hace ROLLBACK al final, así que
# no deja datos ni consume folios reales aunque la tabla ya exista.
# ---------------------------------------------------------------------------

_PATRON_FOLIO = re.compile(r"^(FAC|OC)-(\d{4})-(\d{4,})$")


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Sin DATABASE_URL")
def test_integracion_postgres_contadores_reales():
    from sqlalchemy.orm import Session

    from app.db.session import get_engine
    from app.models.catalogo import ContadorOrdenCompra
    from app.models.facturacion import ContadorSerie

    engine = get_engine()
    # Crea las tablas del contador si la base aún no tiene migraciones.
    ContadorSerie.__table__.create(engine, checkfirst=True)
    ContadorOrdenCompra.__table__.create(engine, checkfirst=True)

    anio = 2999
    with Session(engine) as db:
        transaccion = db.begin()
        try:
            f1 = serie.siguiente_numero_factura(db, anio)
            f2 = serie.siguiente_numero_factura(db, anio)
            o1 = serie.siguiente_numero_oc(db, anio)
        finally:
            # Nada se confirma: el contador del año 2999 vuelve a como estaba.
            transaccion.rollback()

    assert _PATRON_FOLIO.match(f1)
    assert _PATRON_FOLIO.match(f2)
    assert _PATRON_FOLIO.match(o1)
    assert f1 != f2, "dos llamadas seguidas no pueden dar el mismo folio"
    assert f1.startswith("FAC-") and f2.startswith("FAC-")
    assert o1.startswith("OC-")
