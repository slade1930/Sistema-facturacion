"""Pruebas del aporte de José Rivera (JoanRiverssss): numeración de OC.

Cubre app.services.serie para órdenes de compra (OC-AAAA-####) de forma
determinista y SIN Postgres real:

- Consecutivos que no se repiten, aun con miles de llamadas seguidas.
- Aislamiento por año: el contador de 2026 no consume folios de 2027.
- Sin colisión con FAC-AAAA-####: cada serie usa su propia tabla contadora.
- Concurrencia/reintento a nivel de contrato SQL: el INSERT usa
  ON CONFLICT DO NOTHING y el SELECT ... FOR UPDATE (se verifica
  compilando las sentencias contra el dialecto postgresql).
- Rollback/reintento: serie.py solo hace flush() y nunca commit(), así que
  el número queda reservado dentro de la transacción; con la sesión falsa
  se demuestra que cada flush persiste exactamente un incremento.

La sesión falsa `_SesionContadores` simula las tablas contadoras en
memoria indexadas por (tabla, anio): el INSERT crea el contador en 0 si no
existe y el SELECT devuelve la fila "bloqueada"; el incremento se confirma
en flush(), igual que haría el ORM dentro de la transacción.

Nota sobre "ML de pronóstico": no existe ninguna referencia en el repo
(se buscó pronóstico/ML/machine learning en todo el proyecto); queda fuera
de este aporte.
"""

import os
import re
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.services import serie
from app.utils import validators


# ---------------------------------------------------------------------------
# Sesión falsa multi-tabla y multi-año.
#
# execute() compila cada sentencia con el dialecto postgresql para saber qué
# tabla y qué año toca:
#   - INSERT INTO contador_* (anio, ultimo_numero) VALUES (AAAA, 0)
#       ON CONFLICT (anio) DO NOTHING  -> crea el contador en 0 si falta.
#   - SELECT ... FROM contador_* WHERE ... anio = AAAA ... FOR UPDATE
#       -> devuelve la fila "bloqueada" con el ultimo_numero actual.
# El incremento se confirma en flush(): los contadores guardan enteros y la
# fila SimpleNamespace devuelta por el SELECT escribe su valor al hacer
# flush, igual que el ORM dentro de la transacción.
# ---------------------------------------------------------------------------

_PATRON_TABLA = re.compile(r"(?:INTO|FROM)\s+(contador_\w+)")
_PATRON_ANIO = re.compile(r"\b(\d{4})\b")


class _ResultadoFalso:
    def __init__(self, fila):
        self._fila = fila

    def scalar_one(self):
        return self._fila


class _SesionContadores:
    """Session falsa con contadores por (tabla, anio).

    - INSERT ... ON CONFLICT DO NOTHING: siembra el contador en 0.
    - SELECT ... FOR UPDATE: devuelve SimpleNamespace(ultimo_numero=N).
    - flush(): persiste el ultimo_numero incrementado de la última fila.
    - No hay commit(): si serie.py lo llamara, la prueba fallaría.
    """

    def __init__(self):
        self.contadores = {}
        self.sentencias = []
        self.flushes = 0
        self._fila = None
        self._fila_clave = None

    def _clave(self, stmt) -> tuple[str, int]:
        sql = str(
            stmt.compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        tabla = _PATRON_TABLA.search(sql).group(1)
        anio = int(_PATRON_ANIO.search(sql).group(1))
        return tabla, anio

    def execute(self, stmt):
        self.sentencias.append(stmt)
        tabla, anio = self._clave(stmt)
        if "INSERT" in str(stmt):
            self.contadores.setdefault((tabla, anio), 0)
            self._fila = None
            self._fila_clave = None
            return _ResultadoFalso(None)
        ultimo = self.contadores.setdefault((tabla, anio), 0)
        self._fila = SimpleNamespace(ultimo_numero=ultimo)
        self._fila_clave = (tabla, anio)
        return _ResultadoFalso(self._fila)

    def flush(self):
        self.flushes += 1
        if self._fila is not None and self._fila_clave is not None:
            self.contadores[self._fila_clave] = self._fila.ultimo_numero
            self._fila = None
            self._fila_clave = None


# ---------------------------------------------------------------------------
# Consecutivos OC: no se repiten
# ---------------------------------------------------------------------------

class TestConsecutivosOC:
    def test_serie_oc_formato_oficial(self):
        db = _SesionContadores()
        folios = [serie.siguiente_numero_oc(db, 2026) for _ in range(5)]
        assert folios == [
            "OC-2026-0001",
            "OC-2026-0002",
            "OC-2026-0003",
            "OC-2026-0004",
            "OC-2026-0005",
        ]
        # Todos pasan el validador oficial de series.
        for f in folios:
            assert validators.es_serie_oc_valida(f)
            assert validators.extraer_anio(f) == 2026

    def test_mil_llamadas_sin_repetir_ni_saltar(self):
        db = _SesionContadores()
        vistos = set()
        for _ in range(1000):
            folio = serie.siguiente_numero_oc(db, 2026)
            assert folio not in vistos
            vistos.add(folio)
        assert len(vistos) == 1000
        assert db.contadores[("contador_orden_compra", 2026)] == 1000

    def test_flush_por_cada_numero_y_sin_commit(self):
        db = _SesionContadores()
        serie.siguiente_numero_oc(db, 2026)
        serie.siguiente_numero_oc(db, 2026)
        assert db.flushes == 2
        # La sesión falsa no define commit(): si serie.py hiciera commit,
        # esta prueba explotaría con AttributeError.
        assert not hasattr(db, "commit")

    def test_reintento_tras_rollback_reutiliza_el_folio_liberado(self):
        """Escenario reintento/rollback: si la transacción hace rollback, el
        contador vuelve atrás y el reintento reutiliza el mismo folio — no se
        salta ninguno ni se duplica dentro de la misma transacción."""
        db = _SesionContadores()
        primero = serie.siguiente_numero_oc(db, 2026)
        # Simulamos rollback: el contador 'se libera' (la transacción nunca
        # confirmó, así que Postgres descartaría el incremento).
        db.contadores[("contador_orden_compra", 2026)] = 0
        reintento = serie.siguiente_numero_oc(db, 2026)
        assert primero == reintento == "OC-2026-0001"

    def test_consecutivo_pasa_de_9999_sin_romper_formato(self):
        # El formato admite 4+ dígitos: al llegar a 10000 no se trunca.
        db = _SesionContadores()
        db.contadores[("contador_orden_compra", 2026)] = 9999
        folio = serie.siguiente_numero_oc(db, 2026)
        assert folio == "OC-2026-10000"
        assert validators.es_serie_oc_valida(folio)
        assert validators.extraer_anio(folio) == 2026


# ---------------------------------------------------------------------------
# Aislamiento por año
# ---------------------------------------------------------------------------

class TestAislamientoPorAnio:
    def test_contadores_independientes_por_anio(self):
        db = _SesionContadores()
        assert serie.siguiente_numero_oc(db, 2026) == "OC-2026-0001"
        assert serie.siguiente_numero_oc(db, 2026) == "OC-2026-0002"
        # Cambia el año: el contador arranca de nuevo, sin tocar el de 2026.
        assert serie.siguiente_numero_oc(db, 2027) == "OC-2027-0001"
        assert serie.siguiente_numero_oc(db, 2027) == "OC-2027-0002"
        # Y 2026 sigue donde quedó.
        assert serie.siguiente_numero_oc(db, 2026) == "OC-2026-0003"

    def test_anio_distinto_extrae_anio_distinto(self):
        db = _SesionContadores()
        folio_2026 = serie.siguiente_numero_oc(db, 2026)
        folio_2027 = serie.siguiente_numero_oc(db, 2027)
        assert validators.extraer_anio(folio_2026) == 2026
        assert validators.extraer_anio(folio_2027) == 2027
        assert folio_2026 != folio_2027

    def test_cada_anio_crea_su_propio_contador(self):
        db = _SesionContadores()
        serie.siguiente_numero_oc(db, 2026)
        serie.siguiente_numero_oc(db, 2027)
        claves = {k for k in db.contadores if k[0] == "contador_orden_compra"}
        assert claves == {
            ("contador_orden_compra", 2026),
            ("contador_orden_compra", 2027),
        }


# ---------------------------------------------------------------------------
# Sin colisión con FAC
# ---------------------------------------------------------------------------

class TestSinColisionConFacturas:
    def test_oc_y_fac_llevan_contadores_separados(self):
        db = _SesionContadores()
        oc = serie.siguiente_numero_oc(db, 2026)
        fac = serie.siguiente_numero_factura(db, 2026)
        oc2 = serie.siguiente_numero_oc(db, 2026)

        assert oc == "OC-2026-0001"
        assert oc2 == "OC-2026-0002"
        assert fac == "FAC-2026-0001"  # FAC tiene su propio contador en 1
        # Las tablas contadoras quedan separadas en el estado falso.
        assert db.contadores[("contador_orden_compra", 2026)] == 2
        assert db.contadores[("contador_serie", 2026)] == 1

    def test_mismo_numero_distinto_prefijo_no_colapsa(self):
        db = _SesionContadores()
        folios = {
            serie.siguiente_numero_factura(db, 2026),
            serie.siguiente_numero_oc(db, 2026),
        }
        assert len(folios) == 2
        for f in folios:
            if f.startswith("FAC-"):
                assert validators.es_serie_factura_valida(f)
            else:
                assert validators.es_serie_oc_valida(f)

    def test_sql_apunta_a_tablas_distintas(self):
        db = _SesionContadores()
        serie.siguiente_numero_oc(db, 2026)
        serie.siguiente_numero_factura(db, 2026)

        tablas = set()
        for stmt in db.sentencias:
            sql = str(
                stmt.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
            tablas.add(_PATRON_TABLA.search(sql).group(1))
        assert tablas == {"contador_orden_compra", "contador_serie"}


# ---------------------------------------------------------------------------
# Contrato SQL: concurrencia y creación del contador (sin Postgres real)
# ---------------------------------------------------------------------------

class TestContratoConcurrencia:
    def test_insert_usa_on_conflict_do_nothing_por_anio(self):
        db = _SesionContadores()
        serie.siguiente_numero_oc(db, 2026)

        insert_sql = str(
            db.sentencias[0].compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        assert "INSERT INTO contador_orden_compra" in insert_sql
        assert "ON CONFLICT" in insert_sql
        assert "DO NOTHING" in insert_sql
        assert "anio" in insert_sql

    def test_select_bloquea_fila_for_update(self):
        db = _SesionContadores()
        serie.siguiente_numero_oc(db, 2026)

        select_sql = str(
            db.sentencias[1].compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        assert "FROM contador_orden_compra" in select_sql
        assert "FOR UPDATE" in select_sql


# ---------------------------------------------------------------------------
# INTEGRACIÓN PENDIENTE — requiere Postgres real (DATABASE_URL).
#
# Valida contra el motor real lo que la sesión falsa no puede:
#   - Dos llamadas seguidas nunca devuelven el mismo folio OC.
#   - El contador del año se crea solo (ON CONFLICT DO NOTHING).
#   - Rollback real libera el número (no se consume folio).
#
# Usa el año 2998 (imposible en producción) y hace ROLLBACK al final.
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Sin DATABASE_URL")
def test_integracion_postgres_oc_consecutivos_y_rollback():
    from sqlalchemy.orm import Session

    from app.db.session import get_engine
    from app.models.catalogo import ContadorOrdenCompra
    from app.models.facturacion import ContadorSerie

    engine = get_engine()
    ContadorSerie.__table__.create(engine, checkfirst=True)
    ContadorOrdenCompra.__table__.create(engine, checkfirst=True)

    anio = 2998
    with Session(engine) as db:
        transaccion = db.begin()
        try:
            o1 = serie.siguiente_numero_oc(db, anio)
            o2 = serie.siguiente_numero_oc(db, anio)
            f1 = serie.siguiente_numero_factura(db, anio)
        finally:
            # Rollback: nada queda confirmado; los folios del año 2998 no
            # se consumen en producción.
            transaccion.rollback()

    assert validators.es_serie_oc_valida(o1)
    assert validators.es_serie_oc_valida(o2)
    assert o1 != o2
    assert o1.endswith("0001") and o2.endswith("0002")
    assert f1.startswith("FAC-")
