import httpx
import pytest

from ui.state.cliente_api import ClienteApi, ErrorApi


def crear_cliente(manejador, api_key="clave-de-prueba"):
    transport = httpx.MockTransport(manejador)
    return ClienteApi(
        base_url="http://backend:8000",
        api_key=api_key,
        client=httpx.Client(transport=transport),
    )


def test_envia_api_key_en_rutas_privadas():
    vistos = {}

    def manejador(solicitud):
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(200, json={"items": []})

    with crear_cliente(manejador) as cliente:
        assert cliente.get("/api/v1/productos") == {"items": []}

    assert vistos["api_key"] == "clave-de-prueba"


def test_401_levanta_error_api():
    def manejador(solicitud):
        return httpx.Response(
            401,
            json={
                "detail": "API key ausente o inválida.",
                "code": "UNAUTHORIZED",
            },
        )

    with crear_cliente(manejador) as cliente:
        with pytest.raises(ErrorApi) as info:
            cliente.get("/api/v1/productos")

    assert info.value.status_code == 401
    assert info.value.code == "UNAUTHORIZED"
    assert info.value.detail == "API key ausente o inválida."


def test_409_al_anular_dos_veces():
    def manejador(solicitud):
        return httpx.Response(
            409,
            json={"detail": "La factura ya está anulada.", "code": "CONFLICT"},
        )

    with crear_cliente(manejador) as cliente:
        with pytest.raises(ErrorApi) as info:
            cliente.post("/api/v1/facturas/1/anular")

    assert info.value.code == "CONFLICT"


def test_422_incluye_errores():
    cuerpo = {
        "detail": "Datos de entrada inválidos.",
        "code": "VALIDATION_ERROR",
        "errors": [{"loc": ["body", "cliente_nombre"], "msg": "Field required"}],
    }

    def manejador(solicitud):
        return httpx.Response(422, json=cuerpo)

    with crear_cliente(manejador) as cliente:
        with pytest.raises(ErrorApi) as info:
            cliente.post("/api/v1/facturas", json={})

    assert info.value.errors == cuerpo["errors"]


def test_verificacion_publica_no_envia_api_key():
    vistos = {}

    def manejador(solicitud):
        vistos["api_key"] = solicitud.headers.get("X-API-Key")
        return httpx.Response(200, json={"valida": True})

    with crear_cliente(manejador) as cliente:
        assert cliente.get("/api/v1/verificar/FAC-2026-0001/abc") == {"valida": True}

    assert vistos["api_key"] is None


def test_paginacion_del_historial():
    vistos = {}

    def manejador(solicitud):
        vistos["params"] = dict(solicitud.url.params)
        return httpx.Response(
            200,
            json={"items": [], "total": 0, "limite": 10, "desplazamiento": 20},
        )

    with crear_cliente(manejador) as cliente:
        respuesta = cliente.get(
            "/api/v1/historial",
            params={"limite": 10, "desplazamiento": 20},
        )

    assert respuesta["limite"] == 10
    assert vistos["params"]["desplazamiento"] == "20"


def test_pdf_devuelve_bytes():
    def manejador(solicitud):
        return httpx.Response(
            200,
            content=b"%PDF-1.4",
            headers={"Content-Type": "application/pdf"},
        )

    with crear_cliente(manejador) as cliente:
        assert cliente.get("/api/v1/facturas/1/pdf") == b"%PDF-1.4"
