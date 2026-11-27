from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, HTTPException

from app.api.v1.deps import requiere_auth
from app.api.v1.endpoints.facturacion import facturas as facturas_api
from app.api.v1.endpoints.ml import anomalias as endpoint
from app.api.v1.router import router as router_principal
from app.ml.modelos import anomalias as modelo
from app.ml.modelos.anomalias import PrediccionAnomalia
from app.models.facturacion import EstadoFactura
from app.repositories.facturacion import FacturaRepository
from app.schemas.facturacion import FacturaCreate


class DB:
    def __init__(self):
        self.confirmaciones = 0
        self.refrescos = 0

    def commit(self):
        self.confirmaciones += 1

    def refresh(self, _factura):
        self.refrescos += 1

    def flush(self):
        pass


@pytest.fixture
def factura():
    return SimpleNamespace(
        id=7,
        numero_serie="F-7",
        cliente_nombre="Acme",
        cliente_ruc="R-1",
        fecha=date(2026, 11, 27),
        total=Decimal("100.00"),
        itbms=Decimal("7.00"),
        estado=EstadoFactura.EMITIDA,
        en_revision=False,
        puntaje_anomalia=None,
        motivo_anomalia=None,
        lineas=[SimpleNamespace(descuento_pct=Decimal("0.00"))],
    )


def test_ruta_registrada_y_protegida():
    app = FastAPI()
    app.include_router(router_principal, prefix="/api/v1")

    assert "/api/v1/ml/anomalias/evaluar/{factura_id}" in app.openapi()["paths"]
    assert endpoint.router.prefix == "/ml/anomalias"
    assert Depends(requiere_auth) in endpoint.router.dependencies


def test_evaluar_con_modelo_escribe_puntaje_y_motivo_sin_tocar_estado(
    monkeypatch, factura
):
    monkeypatch.setattr(
        FacturaRepository, "obtener_por_id", lambda db, factura_id: factura
    )
    monkeypatch.setattr(
        modelo, "predecir", lambda rasgos: PrediccionAnomalia(0.5377, True)
    )
    db = DB()

    respuesta = endpoint.evaluar_factura(7, db)

    assert respuesta.evaluado is True
    assert respuesta.modelo == modelo.NOMBRE_PUBLICO
    assert respuesta.resultado.factura_id == 7
    assert respuesta.resultado.puntaje_anomalia == Decimal("53.77")
    assert respuesta.resultado.en_revision is True
    assert respuesta.resultado.motivo_anomalia
    assert factura.puntaje_anomalia == Decimal("53.77")
    assert isinstance(factura.puntaje_anomalia, Decimal)
    assert factura.en_revision is True
    assert factura.motivo_anomalia == respuesta.resultado.motivo_anomalia
    assert factura.estado == EstadoFactura.EMITIDA
    assert db.confirmaciones == 1
    assert db.refrescos == 1


def test_evaluar_sin_modelo_no_escribe_ni_cambia_estado(monkeypatch, factura):
    monkeypatch.setattr(
        FacturaRepository, "obtener_por_id", lambda db, factura_id: factura
    )
    monkeypatch.setattr(modelo, "predecir", lambda rasgos: None)
    db = DB()

    respuesta = endpoint.evaluar_factura(7, db)

    assert respuesta.evaluado is False
    assert respuesta.modelo is None
    assert respuesta.resultado.puntaje_anomalia is None
    assert respuesta.resultado.en_revision is False
    assert respuesta.resultado.motivo_anomalia is None
    assert factura.puntaje_anomalia is None
    assert factura.en_revision is False
    assert factura.motivo_anomalia is None
    assert factura.estado == EstadoFactura.EMITIDA
    assert db.confirmaciones == 1


def test_evaluar_factura_inexistente_da_404(monkeypatch):
    monkeypatch.setattr(
        FacturaRepository, "obtener_por_id", lambda db, factura_id: None
    )
    db = DB()

    with pytest.raises(HTTPException) as error:
        endpoint.evaluar_factura(999, db)

    assert error.value.status_code == 404
    assert db.confirmaciones == 0


def test_hook_escribe_sin_hacer_commit(monkeypatch, factura):
    monkeypatch.setattr(
        modelo, "predecir", lambda rasgos: PrediccionAnomalia(0.21, False)
    )

    assert endpoint.evaluar_al_crear(factura) is True
    assert factura.puntaje_anomalia == Decimal("21.00")
    assert factura.en_revision is False
    assert factura.motivo_anomalia
    assert factura.estado == EstadoFactura.EMITIDA


def test_hook_escribe_en_revision_sin_commit(monkeypatch, factura):
    """El flag se guarda en la columna nueva, sin tocar el estado."""
    monkeypatch.setattr(
        modelo, "predecir", lambda rasgos: PrediccionAnomalia(0.82, True)
    )
    db = DB()

    assert endpoint.evaluar_al_crear(factura) is True
    assert factura.en_revision is True
    assert factura.estado == EstadoFactura.EMITIDA
    assert db.confirmaciones == 0


def test_hook_sin_modelo_no_escribe(monkeypatch, factura):
    monkeypatch.setattr(modelo, "predecir", lambda rasgos: None)

    assert endpoint.evaluar_al_crear(factura) is False
    assert factura.puntaje_anomalia is None
    assert factura.en_revision is False
    assert factura.motivo_anomalia is None


def test_hook_con_excepcion_no_bloquea(monkeypatch, factura):
    def fallar(_rasgos):
        raise RuntimeError("modelo roto")

    monkeypatch.setattr(modelo, "predecir", fallar)

    assert endpoint.evaluar_al_crear(factura) is False
    assert factura.puntaje_anomalia is None
    assert factura.estado == EstadoFactura.EMITIDA


def test_crear_factura_sigue_funcionando_si_el_hook_falla(monkeypatch):
    datos = FacturaCreate(
        cliente_nombre="Acme",
        cliente_ruc="R-1",
        lineas=[{"descripcion": "Producto", "cantidad": "1", "precio_unitario": "10.00"}],
    )
    db = DB()
    guardada = {}

    def crear(_db, factura, _lineas, *, commit):
        assert commit is False
        factura.estado = EstadoFactura.EMITIDA
        guardada["factura"] = factura
        return factura

    def fallar(_factura):
        raise RuntimeError("hook roto")

    monkeypatch.setattr(
        facturas_api.ContadorSerieRepository,
        "obtener_siguiente_numero",
        lambda _db, _anio: "F-TEST-1",
    )
    monkeypatch.setattr(facturas_api.FacturaRepository, "crear", crear)
    monkeypatch.setattr(facturas_api, "aplicar_totales", lambda _factura: None)
    monkeypatch.setattr(
        facturas_api, "generar_codigo_verificacion", lambda *_args: "123456789ABC"
    )
    monkeypatch.setattr(endpoint, "evaluar_al_crear", fallar)

    creada = facturas_api.crear_factura(datos, db)

    assert creada is guardada["factura"]
    assert creada.estado == EstadoFactura.EMITIDA
    # El default se aplica al hacer commit; acá sólo importa que el hook no marcó.
    assert creada.en_revision is not True
    assert db.confirmaciones == 1
    assert db.refrescos == 1


def test_hook_pasa_serie_repetida_al_modelo(monkeypatch, factura):
    capturado = []

    def desde(_factura, *, serie_repetida=False):
        capturado.append(serie_repetida)
        return SimpleNamespace()

    monkeypatch.setattr(modelo, "desde_factura", desde)
    monkeypatch.setattr(
        modelo, "predecir", lambda _rasgos: PrediccionAnomalia(0.8, True)
    )

    assert endpoint.evaluar_al_crear(factura, serie_repetida=True) is True
    assert capturado == [True]


def test_evaluar_factura_detecta_serie_repetida(monkeypatch, factura):
    capturado = []

    def desde(_factura, *, serie_repetida=False):
        capturado.append(serie_repetida)
        return SimpleNamespace()

    monkeypatch.setattr(
        FacturaRepository, "obtener_por_id", lambda _db, _id: factura
    )
    monkeypatch.setattr(
        FacturaRepository,
        "existe_numero_serie",
        lambda _db, _serie, excluir_id=None: True,
    )
    monkeypatch.setattr(modelo, "desde_factura", desde)
    monkeypatch.setattr(
        modelo, "predecir", lambda _rasgos: PrediccionAnomalia(0.9, True)
    )

    respuesta = endpoint.evaluar_factura(7, DB())

    assert respuesta.evaluado is True
    assert capturado == [True]
