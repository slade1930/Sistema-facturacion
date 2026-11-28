"""Reglas de acceso y presencia en OpenAPI de las rutas nuevas de administración."""

import pytest
from fastapi.testclient import TestClient

# Cada ruta nueva declara aquí su regla: siempre "admin" (o "sistema" por API-Key).
RUTAS_ADMIN: dict[tuple[str, str], tuple[str, dict | None]] = {
    ("get", "/api/v1/admin/panel/resumen"): ("admin", None),
    ("get", "/api/v1/admin/panel/ingresos"): ("admin", None),
    ("get", "/api/v1/admin/panel/productos"): ("admin", None),
    ("get", "/api/v1/admin/empresas"): ("admin", None),
    ("get", "/api/v1/admin/empresas/{empresa_id}"): ("admin", None),
    ("put", "/api/v1/admin/empresas/{empresa_id}/estado"): (
        "admin",
        {"activo": False},
    ),
    ("get", "/api/v1/admin/catalogo/categorias"): ("admin", None),
    ("get", "/api/v1/admin/catalogo/categorias/{categoria_id}"): ("admin", None),
    ("post", "/api/v1/admin/catalogo/categorias"): (
        "admin",
        {"nombre": "Categoría acceso admin", "sector": "tecnologia"},
    ),
    ("put", "/api/v1/admin/catalogo/categorias/{categoria_id}"): (
        "admin",
        {"nombre": "Categoría acceso admin", "sector": "turismo"},
    ),
    ("get", "/api/v1/admin/catalogo/productos"): ("admin", None),
    ("get", "/api/v1/admin/catalogo/productos/{producto_id}"): ("admin", None),
    ("post", "/api/v1/admin/catalogo/productos"): (
        "admin",
        {
            "categoria_id": 1,
            "nombre": "Producto acceso admin",
            "sku": "SKU-ACCESO-ADMIN",
            "precio_caja": "10.00",
            "precio_unidad": "1.00",
            "unidades_por_caja": 10,
        },
    ),
    ("put", "/api/v1/admin/catalogo/productos/{producto_id}"): (
        "admin",
        {
            "categoria_id": 1,
            "nombre": "Producto acceso admin",
            "sku": "SKU-ACCESO-ADMIN",
            "precio_caja": "10.00",
            "precio_unidad": "1.00",
            "unidades_por_caja": 10,
        },
    ),
    ("put", "/api/v1/admin/catalogo/productos/{producto_id}/estado"): (
        "admin",
        {"activo": False},
    ),
    ("get", "/api/v1/admin/inventario/movimientos"): ("admin", None),
    ("get", "/api/v1/admin/pedidos"): ("admin", None),
    ("get", "/api/v1/admin/pedidos/por-facturar"): ("admin", None),
    ("get", "/api/v1/admin/pedidos/{pedido_id}"): ("admin", None),
    ("get", "/api/v1/admin/auditoria"): ("admin", None),
}

REGISTRO = {
    "nombre_empresa": "Acceso Admin Prueba",
    "ruc": "RUC-ACCESO-ADMIN",
    "direccion": "Calle 1",
    "telefono": "60000002",
    "correo": "acceso-admin@ejemplo.local",
    "sucursal": "Central",
    "contrasena": "Clave1234",
    "sector": "tecnologia",
}


@pytest.fixture
def token_empresa(client: TestClient) -> str:
    respuesta = client.post("/api/v1/auth/registro", json=REGISTRO)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["token"]


def _llamar(client: TestClient, metodo: str, ruta: str, cuerpo: dict | None, headers: dict):
    for parametro in ("{empresa_id}", "{categoria_id}", "{producto_id}", "{pedido_id}"):
        ruta = ruta.replace(parametro, "1")
    funcion = getattr(client, metodo)
    if cuerpo is None:
        return funcion(ruta, headers=headers)
    return funcion(ruta, headers=headers, json=cuerpo)


def test_admin_openapi_declara_todas_las_rutas_y_su_regla(client: TestClient):
    esquema = client.get("/openapi.json").json()["paths"]
    for (metodo, ruta), (regla, _cuerpo) in RUTAS_ADMIN.items():
        assert regla == "admin"
        assert ruta in esquema, ruta
        assert metodo in esquema[ruta], (metodo, ruta)
        if ruta != "/api/v1/admin/inventario/movimientos":
            respuestas = esquema[ruta][metodo]["responses"]
            assert "401" in respuestas, (metodo, ruta)
            assert "403" in respuestas, (metodo, ruta)


def test_admin_rutas_nuevas_dan_401_sin_autenticacion(client: TestClient):
    for (metodo, ruta), (_regla, cuerpo) in RUTAS_ADMIN.items():
        respuesta = _llamar(client, metodo, ruta, cuerpo, {"X-API-Key": ""})
        assert respuesta.status_code == 401, (metodo, ruta, respuesta.text)


def test_admin_rutas_nuevas_dan_403_a_empresa(client: TestClient, token_empresa: str):
    headers = {"Authorization": "Bearer " + token_empresa}
    for (metodo, ruta), (_regla, cuerpo) in RUTAS_ADMIN.items():
        respuesta = _llamar(client, metodo, ruta, cuerpo, headers)
        assert respuesta.status_code == 403, (metodo, ruta, respuesta.text)
