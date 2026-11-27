"""Pruebas de la numeración de órdenes de compra (OC-AAAA-####).

Cubre: formato, incremento consecutivo, sin duplicados, reinicio por año,
independencia respecto a FAC, rollback sin huecos y concurrencia real.
Requiere PostgreSQL (serie.py usa ON CONFLICT y FOR UPDATE).
"""

import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import delete

from app.models.catalogo import ContadorOrdenCompra
from app.services.serie import (
    _formato,
    siguiente_numero_factura,
    siguiente_numero_oc,
)

PATRON_OC = re.compile(r"^OC-\d{4}-\d{4}$")

# Años lejanos para no chocar con datos reales de la base de pruebas.
ANIO = 2091
ANIO_SIGUIENTE = 2092
ANIO_CONCURRENCIA = 2093


# ---------- Formato ----------

def test_formato_rellena_con_ceros():
    assert _formato("OC", 2026, 7) == "OC-2026-0007"


def test_formato_oc_valido(db):
    numero = siguiente_numero_oc(db, ANIO)
    assert PATRON_OC.match(numero)
    assert numero.startswith(f"OC-{ANIO}-")


def test_pasa_de_9999_a_cinco_digitos(db):
    # Documenta el comportamiento: :04d no recorta, el folio crece a 5 dígitos.
    assert _formato("OC", ANIO, 9999) == f"OC-{ANIO}-9999"
    assert _formato("OC", ANIO, 10000) == f"OC-{ANIO}-10000"


# ---------- Consecutivos y sin duplicados ----------

def test_primer_numero_es_0001(db):
    assert siguiente_numero_oc(db, ANIO) == f"OC-{ANIO}-0001"


def test_numeros_seguidos(db):
    numeros = [siguiente_numero_oc(db, ANIO) for _ in range(5)]
    assert numeros == [f"OC-{ANIO}-{i:04d}" for i in range(1, 6)]


def test_lote_grande_sin_duplicados_ni_huecos(db):
    numeros = [siguiente_numero_oc(db, ANIO) for _ in range(200)]
    assert len(numeros) == len(set(numeros))
    consecutivos = [int(n.split("-")[2]) for n in numeros]
    assert consecutivos == list(range(1, 201))


# ---------- Cambio de año ----------

def test_reinicia_en_0001_al_cambiar_de_anio(db):
    siguiente_numero_oc(db, ANIO)
    siguiente_numero_oc(db, ANIO)
    assert siguiente_numero_oc(db, ANIO_SIGUIENTE) == f"OC-{ANIO_SIGUIENTE}-0001"
    # el año anterior conserva su propio contador
    assert siguiente_numero_oc(db, ANIO) == f"OC-{ANIO}-0003"


# ---------- Independencia de FAC ----------

def test_oc_y_factura_tienen_contadores_separados(db):
    assert siguiente_numero_factura(db, ANIO) == f"FAC-{ANIO}-0001"
    assert siguiente_numero_factura(db, ANIO) == f"FAC-{ANIO}-0002"
    # las facturas no movieron el contador de OC
    assert siguiente_numero_oc(db, ANIO) == f"OC-{ANIO}-0001"
    # y las OC no mueven el de facturas
    assert siguiente_numero_factura(db, ANIO) == f"FAC-{ANIO}-0003"


# ---------- Rollback (solo flush, nunca commit) ----------

def test_rollback_libera_el_numero(db):
    primero = siguiente_numero_oc(db, ANIO)
    assert primero == f"OC-{ANIO}-0001"
    db.rollback()  # el pedido falló: el número no debe quedar consumido
    assert siguiente_numero_oc(db, ANIO) == f"OC-{ANIO}-0001"


# ---------- Concurrencia real ----------

def _tomar_numero(session_factory, anio):
    # Cada hilo usa su propia sesión/transacción. El commit libera el bloqueo.
    with session_factory() as s:
        numero = siguiente_numero_oc(s, anio)
        s.commit()
        return numero


@pytest.fixture
def limpiar_concurrencia(session_factory):
    yield
    with session_factory() as s:
        s.execute(
            delete(ContadorOrdenCompra).where(
                ContadorOrdenCompra.anio == ANIO_CONCURRENCIA
            )
        )
        s.commit()


def test_concurrencia_no_repite_ni_salta(session_factory, limpiar_concurrencia):
    # El contador del año NO existe todavía: prueba también el ON CONFLICT DO NOTHING.
    with ThreadPoolExecutor(max_workers=10) as pool:
        resultados = list(
            pool.map(lambda _: _tomar_numero(session_factory, ANIO_CONCURRENCIA), range(50))
        )
    assert len(resultados) == 50
    assert len(set(resultados)) == 50  # ninguno repetido
    numeros = sorted(int(r.split("-")[2]) for r in resultados)
    assert numeros == list(range(1, 51))  # del 1 al 50, sin huecos
