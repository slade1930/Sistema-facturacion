import json
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.ml import asistente as endpoint
from app.api.v1.router import router as router_principal
from app.core import errors
from app.ml.asistente import catalogo, intenciones
from app.ml.modelos import asistente as modelo

HOY = date(2026, 11, 26)


class DB:
    def __init__(self):
        self.confirmaciones = 0

    def commit(self):
        self.confirmaciones += 1


@pytest.fixture
def hoy_fijo(monkeypatch):
    monkeypatch.setattr(endpoint, "date", SimpleNamespace(today=lambda: HOY))
    return HOY


def test_endpoint_consultar_esta_preparado_para_registrar():
    rutas = [ruta for ruta in endpoint.router.routes if ruta.path.endswith("/consultar")]
    assert len(rutas) == 1
    assert "POST" in rutas[0].methods
    assert endpoint.router.prefix == "/ml/asistente"


def test_ruta_registrada_en_el_router_principal():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router_principal, prefix="/api/v1")
    assert "/api/v1/ml/asistente/consultar" in app.openapi()["paths"]


def test_sin_modelo_responde_desde_catalogo_con_hoy(monkeypatch, hoy_fijo):
    monkeypatch.setattr(modelo, "predecir", lambda *args, **kwargs: None)
    capturado = {}

    def consulta(db, **kwargs):
        capturado.update(kwargs)
        return {
            "consulta": "ventas_por_mes",
            "datos": [{"mes": "2026-11", "total": "25.00"}],
            "total": "25.00",
        }

    monkeypatch.setitem(catalogo.CATALOGO, "ventas_por_mes", consulta)
    db = DB()

    respuesta = endpoint.consultar(endpoint.ConsultaAsistente(pregunta="Ventas de este mes"), db)

    assert respuesta["evaluado"] is False
    assert respuesta["modelo"] == endpoint.NOMBRE_LINEA_BASE
    assert respuesta["resultado"]["intencion"] == "ventas_por_mes"
    assert respuesta["resultado"]["datos"] == [{"mes": "2026-11", "total": "25.00"}]
    assert capturado["hoy"] == hoy_fijo
    assert capturado["anio"] == 2026
    assert capturado["mes"] == 11
    assert db.confirmaciones == 0


def test_con_modelo_responde_con_la_intencion_predicha(monkeypatch, hoy_fijo):
    prediccion = intenciones.Intencion(
        "ventas_por_cliente", 0.93, {"cliente": "acme"}
    )
    monkeypatch.setattr(modelo, "predecir", lambda *args, **kwargs: prediccion)
    capturado = {}

    def consulta(db, **kwargs):
        capturado.update(kwargs)
        return {"consulta": "ventas_por_cliente", "datos": [], "total": "0.00"}

    monkeypatch.setitem(catalogo.CATALOGO, "ventas_por_cliente", consulta)
    db = DB()

    respuesta = endpoint.consultar(
        endpoint.ConsultaAsistente(pregunta="Ventas por cliente Acme"), db
    )

    assert respuesta["evaluado"] is True
    assert respuesta["modelo"] == modelo.NOMBRE_PUBLICO
    assert respuesta["resultado"]["intencion"] == "ventas_por_cliente"
    assert respuesta["resultado"]["confianza"] == 0.93
    assert capturado["cliente"] == "acme"
    assert capturado["hoy"] == hoy_fijo
    assert db.confirmaciones == 0


def test_no_entendi_cuando_no_hay_confianza(monkeypatch, hoy_fijo):
    monkeypatch.setattr(modelo, "predecir", lambda *args, **kwargs: None)
    monkeypatch.setattr(intenciones, "clasificar", lambda *args, **kwargs: None)

    def consulta(db, **kwargs):
        raise AssertionError("no se debe consultar el catálogo")

    monkeypatch.setitem(catalogo.CATALOGO, "ventas_por_mes", consulta)

    respuesta = endpoint.consultar(
        endpoint.ConsultaAsistente(pregunta="Hola, ¿cómo estás?"), DB()
    )

    assert respuesta["evaluado"] is False
    assert respuesta["modelo"] == endpoint.NOMBRE_LINEA_BASE
    assert respuesta["resultado"]["intencion"] is None
    assert respuesta["resultado"]["confianza"] is None
    assert respuesta["resultado"]["datos"] == []
    assert "No entendí" in respuesta["resultado"]["respuesta"]


def test_pregunta_vacia_da_error_con_codigo():
    with pytest.raises(HTTPException) as error:
        endpoint.consultar(endpoint.ConsultaAsistente(pregunta="   "), DB())

    assert error.value.status_code == 422
    cuerpo = json.loads(errors.manejar_http_error(None, error.value).body)
    assert cuerpo == {
        "detail": "La pregunta no puede estar vacía.",
        "code": "VALIDATION_ERROR",
    }


def test_fallo_de_la_consulta_da_error_con_codigo(monkeypatch, hoy_fijo):
    monkeypatch.setattr(modelo, "predecir", lambda *args, **kwargs: None)

    def consulta(db, **kwargs):
        raise ValueError("fecha fuera de rango")

    monkeypatch.setitem(catalogo.CATALOGO, "ventas_por_mes", consulta)

    with pytest.raises(HTTPException) as error:
        endpoint.consultar(
            endpoint.ConsultaAsistente(pregunta="Ventas por mes"), DB()
        )

    assert error.value.status_code == 422
    cuerpo = json.loads(errors.manejar_http_error(None, error.value).body)
    assert cuerpo == {"detail": "fecha fuera de rango", "code": "VALIDATION_ERROR"}
