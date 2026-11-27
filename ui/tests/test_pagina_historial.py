import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.facturacion.historial import consultar, filas
from state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        client=httpx.Client(transport=transport),
    )


def test_consultar_envia_filtros_y_paginacion():
    vistos = {}

    def manejador(solicitud):
        vistos["params"] = dict(solicitud.url.params)
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(
            200,
            json={"items": [], "total": 0, "limite": 10, "desplazamiento": 20},
        )

    filtros = {
        "cliente": "Pérez",
        "estado": "emitida",
        "fecha_desde": "2026-11-01",
        "fecha_hasta": "2026-11-27",
        "limite": 10,
        "desplazamiento": 20,
    }

    with crear_cliente(manejador) as cliente_api:
        datos = consultar(cliente_api, filtros)

    assert datos["limite"] == 10
    assert datos["desplazamiento"] == 20
    assert vistos["params"]["cliente"] == "Pérez"
    assert vistos["params"]["estado"] == "emitida"
    assert vistos["params"]["fecha_desde"] == "2026-11-01"
    assert vistos["params"]["fecha_hasta"] == "2026-11-27"
    assert vistos["params"]["limite"] == "10"
    assert vistos["params"]["desplazamiento"] == "20"
    assert vistos["api_key"] == "clave-de-prueba"


def test_consultar_omite_filtros_vacios():
    vistos = {}

    def manejador(solicitud):
        vistos["params"] = dict(solicitud.url.params)
        return httpx.Response(
            200,
            json={"items": [], "total": 0, "limite": 20, "desplazamiento": 0},
        )

    with crear_cliente(manejador) as cliente_api:
        consultar(cliente_api, {"cliente": "", "estado": "", "limite": 20})

    assert "cliente" not in vistos["params"]
    assert "estado" not in vistos["params"]
    assert "fecha_desde" not in vistos["params"]
    assert "fecha_hasta" not in vistos["params"]
    assert vistos["params"]["limite"] == "20"
    assert vistos["params"]["desplazamiento"] == "0"


def test_consultar_401_es_unauthorized():
    def manejador(solicitud):
        return httpx.Response(
            401,
            json={"detail": "API key ausente o inválida.", "code": "UNAUTHORIZED"},
        )

    with crear_cliente(manejador) as cliente_api:
        try:
            consultar(cliente_api, {})
        except ErrorApi as error:
            assert error.status_code == 401
            assert error.code == "UNAUTHORIZED"
            assert error.detail == "API key ausente o inválida."
        else:
            raise AssertionError("Se esperaba ErrorApi")


def test_filas_mapea_resumen():
    item = {
        "id": 7,
        "numero_serie": "FAC-2026-0007",
        "fecha": "2026-11-27",
        "cliente_nombre": "Cliente Prueba",
        "condicion_pago": "contado",
        "total": "10.50",
        "estado": "emitida",
        "extra": "no se muestra",
    }

    resultado = filas([item])

    assert resultado == [
        {
            "id": 7,
            "numero_serie": "FAC-2026-0007",
            "fecha": "2026-11-27",
            "cliente_nombre": "Cliente Prueba",
            "condicion_pago": "contado",
            "total": "10.50",
            "estado": "emitida",
        }
    ]
