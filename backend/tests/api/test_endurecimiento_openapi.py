"""Toda ruta del OpenAPI debe tener una regla de acceso declarada."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Regla declarada para cada operación: público, API-Key, admin, empresa, ml,
# auth pública (login/registro) o auth con sesión (yo/logout/cambiar-clave).
REGLAS: dict[tuple[str, str], str] = {
    ("GET", "/health"): "publico",
    ("GET", "/api/v1/verificar/{numero_serie}/{codigo}"): "publico",
    ("POST", "/api/v1/auth/login"): "auth_publico",
    ("POST", "/api/v1/auth/registro"): "auth_publico",
    ("GET", "/api/v1/auth/yo"): "auth_sesion",
    ("POST", "/api/v1/auth/logout"): "auth_sesion",
    ("POST", "/api/v1/auth/cambiar-clave"): "auth_sesion",
    ("POST", "/api/v1/compras"): "empresa",
    ("POST", "/api/v1/ml/anomalias/evaluar/{factura_id}"): "ml",
    ("POST", "/api/v1/ml/asistente/consultar"): "ml",
    ("GET", "/api/v1/ml/pronostico"): "ml",
    ("GET", "/api/v1/ml/recomendaciones"): "ml",
    ("GET", "/api/v1/admin/inventario"): "admin",
    ("GET", "/api/v1/admin/inventario/{producto_id}/movimientos"): "admin",
    ("PUT", "/api/v1/admin/inventario/{producto_id}"): "admin",
    ("GET", "/api/v1/admin/resumen"): "admin",
    ("GET", "/api/v1/configuracion"): "admin",
    ("PUT", "/api/v1/configuracion"): "admin",
    ("POST", "/api/v1/configuracion/logo"): "admin",
    ("POST", "/api/v1/categorias"): "admin",
    ("PUT", "/api/v1/categorias/{categoria_id}"): "admin",
    ("POST", "/api/v1/clientes"): "admin",
    ("PUT", "/api/v1/clientes/{cliente_id}"): "admin",
    ("DELETE", "/api/v1/clientes/{cliente_id}"): "admin",
    ("POST", "/api/v1/productos"): "admin",
    ("PUT", "/api/v1/productos/{producto_id}"): "admin",
    ("DELETE", "/api/v1/productos/{producto_id}"): "admin",
    ("POST", "/api/v1/facturas"): "admin",
    ("POST", "/api/v1/facturas/{factura_id}/anular"): "admin",
    ("POST", "/api/v1/facturas/{factura_id}/duplicar"): "admin",
    ("POST", "/api/v1/pedidos/{pedido_id}/facturar"): "admin",
    ("GET", "/api/v1/catalogo/buscar"): "api_key",
    ("GET", "/api/v1/categorias"): "api_key",
    ("GET", "/api/v1/categorias/{categoria_id}"): "api_key",
    ("GET", "/api/v1/clientes"): "api_key",
    ("GET", "/api/v1/clientes/{cliente_id}"): "api_key",
    ("GET", "/api/v1/productos"): "api_key",
    ("GET", "/api/v1/productos/{producto_id}"): "api_key",
    ("GET", "/api/v1/facturas/{factura_id}"): "api_key",
    ("GET", "/api/v1/facturas/{factura_id}/pdf"): "api_key",
    ("GET", "/api/v1/historial"): "api_key",
    ("GET", "/api/v1/pedidos"): "api_key",
    ("GET", "/api/v1/pedidos/por-facturar"): "api_key",
    ("GET", "/api/v1/pedidos/{pedido_id}"): "api_key",
    ("POST", "/api/v1/pedidos"): "api_key",
    ("POST", "/api/v1/carrito/calcular"): "api_key",
}

# FastAPI no incluye la documentación en el esquema, pero son rutas públicas.
RUTAS_DOCUMENTACION: dict[tuple[str, str], str] = {
    ("GET", "/docs"): "publico",
    ("GET", "/docs/oauth2-redirect"): "publico",
    ("GET", "/openapi.json"): "publico",
    ("GET", "/redoc"): "publico",
}

REGLAS_PERMITIDAS = {
    "publico",
    "api_key",
    "admin",
    "empresa",
    "ml",
    "auth_publico",
    "auth_sesion",
}
REGLAS_SIN_ACCESO = {"publico", "auth_publico"}


def _operaciones() -> set[tuple[str, str]]:
    esquema = app.openapi()
    return {
        (metodo.upper(), ruta)
        for ruta, metodos in esquema["paths"].items()
        for metodo in metodos
    }


def _ruta_concretada(ruta: str) -> str:
    for nombre in (
        "factura_id",
        "pedido_id",
        "producto_id",
        "cliente_id",
        "categoria_id",
        "numero_serie",
        "codigo",
    ):
        ruta = ruta.replace("{" + nombre + "}", "1")
    return ruta


def test_endurecimiento_openapi_todas_las_rutas_tienen_regla():
    operaciones = _operaciones()

    sin_declarar = operaciones - set(REGLAS)
    sobrantes = set(REGLAS) - operaciones
    assert not sin_declarar, f"Rutas sin regla de acceso: {sorted(sin_declarar)}"
    assert not sobrantes, f"Reglas sin ruta vigente: {sorted(sobrantes)}"
    assert set(REGLAS.values()) <= REGLAS_PERMITIDAS


def test_endurecimiento_openapi_reglas_efectivas_sin_credenciales(client: TestClient):
    declaradas = REGLAS | RUTAS_DOCUMENTACION
    for (metodo, ruta), regla in sorted(declaradas.items()):
        respuesta = client.request(
            metodo,
            _ruta_concretada(ruta),
            headers={"X-API-Key": ""},
        )
        detalle = f"{metodo} {ruta} ({regla}): {respuesta.status_code}"
        if regla in REGLAS_SIN_ACCESO:
            assert respuesta.status_code != 401, detalle
        else:
            assert respuesta.status_code == 401, detalle
