"""Pruebas del endpoint GET /ml/pronostico sin base de datos real.

Además de la app mínima con un `get_db` falso, se verifica que el router
ya quedó registrado y protegido en `app/api/v1/router.py`.
"""
import math

import joblib
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.v1.deps import requiere_auth
from app.api.v1.endpoints.ml import pronostico as ep
from app.api.v1.endpoints.ml.pronostico import router
from app.api.v1.router import router as router_principal
from app.core.errors import registrar_manejadores
from app.db.session import get_db
from app.ml.inferencia import cargador
from app.ml.modelos import pronostico as modelos
from app.ml.modelos import pronostico_lstm as modelos_lstm


def test_ruta_registrada_y_protegida():
    app = FastAPI()
    app.include_router(router_principal, prefix="/api/v1")

    assert "/api/v1/ml/pronostico" in app.openapi()["paths"]
    assert Depends(requiere_auth) in ep.router.dependencies


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "clave-prueba-ml")
    monkeypatch.setattr(cargador, "CARPETA_MODELOS", tmp_path / "ml_models")
    (tmp_path / "ml_models").mkdir(exist_ok=True)

    app = FastAPI()
    registrar_manejadores(app)
    app.include_router(router, prefix="/api/v1")

    def _db_falso():
        yield object()  # nunca se usa cuando no hay serie que consultar

    app.dependency_overrides[get_db] = _db_falso
    return TestClient(app, headers={"X-API-Key": "clave-prueba-ml"})


def test_sin_modelo_responde_sin_evaluar(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    r = client.get("/api/v1/ml/pronostico")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo == {"evaluado": False, "modelo": None, "resultado": None}


def test_con_modelo_devuelve_pronostico(tmp_path, monkeypatch):
    statsmodels = pytest.importorskip("statsmodels")
    client = _app(tmp_path, monkeypatch)
    # Entrenamos el clásico con una serie sintética y lo dejamos en ml_models.
    serie = [
        100 + 20 * math.sin(2 * math.pi * i / 12) + i * 0.5
        for i in range(48)
    ]
    modelo = modelos.entrenar_modelo(serie, horizonte=6)
    joblib.dump(modelo, tmp_path / "ml_models" / "pronostico_clasico.joblib")

    # Serie "de BD" falsa: 48 meses sintéticos.
    periodos, valores = [], []
    anio, mes = 2022, 1
    for v in serie:
        periodos.append(f"{anio:04d}-{mes:02d}")
        valores.append(round(v, 2))
        mes += 1
        if mes > 12:
            mes, anio = 1, anio + 1
    monkeypatch.setattr(ep, "_serie_desde_db", lambda db, pid=None: (periodos, valores))

    r = client.get("/api/v1/ml/pronostico?meses=3")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["evaluado"] is True
    assert cuerpo["modelo"] == "pronostico_clasico.joblib"
    res = cuerpo["resultado"]
    assert res["nivel"] == "total"
    assert res["horizonte"] == 3
    assert len(res["valores"]) == 3
    assert len(res["periodos"]) == 3
    assert res["periodos"][0] > periodos[-1]


def test_con_modelo_sin_datos_devuelve_sin_evaluar(tmp_path, monkeypatch):
    statsmodels = pytest.importorskip("statsmodels")
    client = _app(tmp_path, monkeypatch)
    modelo = modelos.entrenar_modelo(
        [float(i) for i in range(30, 78)], horizonte=6
    )
    joblib.dump(modelo, tmp_path / "ml_models" / "pronostico_clasico.joblib")
    monkeypatch.setattr(ep, "_serie_desde_db", lambda db, pid=None: ([], []))

    r = client.get("/api/v1/ml/pronostico")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["evaluado"] is False
    assert cuerpo["resultado"]["estado"] == "sin evaluar"


def test_mes_fuera_de_rango_da_422(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    r = client.get("/api/v1/ml/pronostico?meses=99")
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["code"] == "VALIDATION_ERROR"
    assert isinstance(cuerpo["detail"], str)


def test_endpoint_lstm_con_meses_distinto_de_seis(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    client = _app(tmp_path, monkeypatch)
    serie = [100 + 10 * (i % 3) + i * 2 for i in range(30)]
    modelo = modelos_lstm.entrenar_lstm(
        serie, horizonte=6, epocas=3, semilla=1
    )
    modelos_lstm.guardar_modelo(modelo, tmp_path / "ml_models")
    periodos = [f"2024-{i:02d}" for i in range(1, 13)]
    monkeypatch.setattr(
        ep, "_serie_desde_db", lambda db, pid=None: (periodos, serie[:12])
    )

    r = client.get("/api/v1/ml/pronostico?meses=3")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["evaluado"] is True
    assert cuerpo["modelo"] == "pronostico_lstm.pt"
    assert cuerpo["resultado"]["horizonte"] == 3
    assert len(cuerpo["resultado"]["valores"]) == 3

    r = client.get("/api/v1/ml/pronostico?meses=12")
    assert r.json()["resultado"]["motivo"] == "sin predicción"
