"""Pruebas del endpoint GET /ml/recomendaciones (Módulo 3).

Se usa una app mínima con repositorios falsos: sin PostgreSQL y sin
artefactos entrenados. También se verifica que el router quedó
registrado y protegido en `app/api/v1/router.py`.
"""
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.v1.deps import requiere_auth
from app.api.v1.endpoints.ml import recomendaciones as endpoint
from app.api.v1.router import router as router_principal
from app.core.errors import registrar_manejadores
from app.db.session import get_db
from app.ml.inferencia import cargador
from app.ml.modelos import recomendaciones as modelo


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "clave-prueba-ml")

    class Productos:
        def listar(self, *, solo_activos=True, limit=100):
            return [
                SimpleNamespace(id=1),
                SimpleNamespace(id=2),
                SimpleNamespace(id=3),
                SimpleNamespace(id=4),
            ]

    class Pedidos:
        def __init__(self, _db):
            pass

        def listar(self, *, skip=0, limit=100):
            return [
                SimpleNamespace(
                    id=1,
                    cliente_id=1,
                    estado="pendiente",
                    fecha_creacion=None,
                    lineas=[
                        SimpleNamespace(producto_id=1, cantidad=1, monto=10, subtotal=10),
                        SimpleNamespace(producto_id=2, cantidad=1, monto=20, subtotal=20),
                    ],
                )
            ]

    monkeypatch.setattr(endpoint, "ProductoRepository", lambda db: Productos())
    monkeypatch.setattr(endpoint, "PedidoB2BRepository", Pedidos)
    monkeypatch.setattr(
        endpoint.FacturaRepository,
        "listar",
        staticmethod(lambda db, **kwargs: []),
    )
    monkeypatch.setattr(cargador, "CARPETA_MODELOS", None)

    app = FastAPI()
    registrar_manejadores(app)
    app.include_router(endpoint.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: object()
    with TestClient(app) as cliente:
        yield cliente


def _get(cliente, query=""):
    return cliente.get(
        "/api/v1/ml/recomendaciones" + query,
        headers={"X-API-Key": "clave-prueba-ml"},
    )


def test_ruta_registrada_y_protegida():
    app = FastAPI()
    app.include_router(router_principal, prefix="/api/v1")
    assert "/api/v1/ml/recomendaciones" in app.openapi()["paths"]
    assert any(
        Depends(requiere_auth) in (r.dependencies or [])
        for r in endpoint.router.routes
    )


def test_sin_api_key_da_401(client):
    respuesta = client.get("/api/v1/ml/recomendaciones")
    assert respuesta.status_code == 401


def test_sin_modelo_cae_a_reglas_o_mas_vendidos(client, monkeypatch):
    monkeypatch.setattr(endpoint, "_cargar_modelo", lambda: None)
    respuesta = _get(client, "?producto_ids=1&n=2")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["modelo"] is None
    assert datos["resultado"]["producto_ids"] == [1]
    assert len(datos["resultado"]["recomendaciones"]) <= 2
    assert all(item["producto_id"] != 1 for item in datos["resultado"]["recomendaciones"])


def test_excluye_carrito_e_inactivos(client, monkeypatch):
    monkeypatch.setattr(endpoint, "_cargar_modelo", lambda: None)

    class Productos:
        def listar(self, *, solo_activos=True, limit=100):
            return [SimpleNamespace(id=1), SimpleNamespace(id=3)]

    monkeypatch.setattr(endpoint, "ProductoRepository", lambda db: Productos())
    respuesta = _get(client, "?producto_ids=1,9&n=5")
    assert respuesta.status_code == 200, respuesta.text
    ids = [
        item["producto_id"]
        for item in respuesta.json()["resultado"]["recomendaciones"]
    ]
    assert 1 not in ids  # en el carrito
    assert 2 not in ids  # dado de baja
    assert 9 not in ids  # en el carrito
    assert set(ids) <= {3}


def test_autoencoder_sin_productos_activos_cae_a_reglas(client, monkeypatch):
    """El artefacto del dataset puede tener ids ajenos a la base real."""
    torch = pytest.importorskip("torch")
    import pandas as pd

    matriz = pd.DataFrame(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0, 0.0],
        ],
        index=["A", "B", "C", "D"],
        columns=[101, 102, 103, 104],
    )
    artefacto = modelo.entrenar_autoencoder(matriz, ocultas=4, epocas=5)
    assert artefacto is not None
    monkeypatch.setattr(endpoint, "_cargar_modelo", lambda: artefacto)

    respuesta = _get(client, "?producto_ids=1&n=2")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["modelo"] is None
    ids = [
        item["producto_id"]
        for item in datos["resultado"]["recomendaciones"]
    ]
    assert ids and set(ids) <= {2, 3, 4}  # activos del fixture
    assert not (set(ids) & {101, 102, 103, 104})  # nunca los ids del artefacto


def test_con_autoencoder_devuelve_modelo(client, monkeypatch):
    torch = pytest.importorskip("torch")
    import pandas as pd

    matriz = pd.DataFrame(
        [
            [1.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
        ],
        index=["A", "B", "C", "D", "E"],
        columns=[1, 2, 3, 4],
    )
    artefacto = modelo.entrenar_autoencoder(matriz, ocultas=4, epocas=5)
    assert artefacto is not None
    monkeypatch.setattr(endpoint, "_cargar_modelo", lambda: artefacto)

    respuesta = _get(client, "?producto_ids=1&n=2")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["modelo"] == modelo.NOMBRE_MODELO
    assert len(datos["resultado"]["recomendaciones"]) == 2
    assert all(
        item["fuente"] == "autoencoder"
        for item in datos["resultado"]["recomendaciones"]
    )
