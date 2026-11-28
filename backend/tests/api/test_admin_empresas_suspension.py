"""Suspensión, reactivación y filtros del listado admin de empresas."""

import pytest
from fastapi.testclient import TestClient

from app.services.auth import limpiar_intentos

NOMBRE_1 = "Empresa Admin Suspension Uno"
NOMBRE_2 = "Empresa Admin Suspension Dos"
CLAVE = "Clave1234"


@pytest.fixture(autouse=True)
def sin_intentos_acumulados():
    """El límite de fallos es en memoria; cada prueba empieza limpia."""
    nombres = (NOMBRE_1, NOMBRE_2)
    for nombre in nombres:
        limpiar_intentos("testclient", nombre)
    yield
    for nombre in nombres:
        limpiar_intentos("testclient", nombre)


def _registrar(client: TestClient, nombre: str, ruc: str, sector: str) -> int:
    respuesta = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre_empresa": nombre,
            "ruc": ruc,
            "direccion": "Calle Admin 1",
            "telefono": "60000009",
            "correo": f"{sector}-admin-susp@ejemplo.local",
            "sucursal": "Central",
            "contrasena": CLAVE,
            "sector": sector,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["cuenta_id"]


def _login(client: TestClient, nombre: str, clave: str = CLAVE):
    return client.post(
        "/api/v1/auth/login",
        json={"nombre_empresa": nombre, "contrasena": clave},
    )


def test_admin_suspender_empresa_revoca_sesion_bloquea_login_y_audita(client):
    cuenta_id = _registrar(client, NOMBRE_1, "RUC-ADM-SUSP-1", "tecnologia")
    sesion = _login(client, NOMBRE_1)
    assert sesion.status_code == 200, sesion.text
    token = sesion.json()["token"]

    respuesta = client.put(
        f"/api/v1/admin/empresas/{sesion.json()['empresa']['id']}/estado",
        json={"activo": False, "motivo": "Suspensión de prueba"},
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["activo"] is False
    assert datos["cuenta_activa"] is False

    antigua = client.get(
        "/api/v1/admin/auditoria",
        headers={"Authorization": "Bearer " + token},
    )
    assert antigua.status_code == 401, antigua.text

    nuevo_login = _login(client, NOMBRE_1)
    assert nuevo_login.status_code == 401, nuevo_login.text

    auditoria = client.get(
        "/api/v1/admin/auditoria", params={"accion": "empresa_suspendida"}
    )
    assert auditoria.status_code == 200, auditoria.text
    eventos = auditoria.json()["items"]
    assert any("Suspensión de prueba" in (e["detalle"] or "") for e in eventos)
    assert all(e["cuenta_id"] is None for e in eventos)

    detalle = client.get(f"/api/v1/admin/empresas/{datos['id']}")
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["cuenta_activa"] is False
    assert detalle.json()["activo"] is False
    assert cuenta_id  # La cuenta suspendida es la que se consultó.


def test_admin_reactivar_empresa_permite_login_nuevo(client):
    cuenta_id = _registrar(client, NOMBRE_2, "RUC-ADM-SUSP-2", "turismo")
    empresa_id = client.get(
        "/api/v1/admin/empresas", params={"busqueda": NOMBRE_2}
    ).json()["items"][0]["id"]

    suspension = client.put(
        f"/api/v1/admin/empresas/{empresa_id}/estado",
        json={"activo": False},
    )
    assert suspension.status_code == 200, suspension.text
    assert _login(client, NOMBRE_2).status_code == 401

    activacion = client.put(
        f"/api/v1/admin/empresas/{empresa_id}/estado",
        json={"activo": True, "motivo": "Reactivación de prueba"},
    )
    assert activacion.status_code == 200, activacion.text
    assert activacion.json()["activo"] is True
    assert activacion.json()["cuenta_activa"] is True

    login = _login(client, NOMBRE_2)
    assert login.status_code == 200, login.text
    assert login.json()["cuenta_id"] == cuenta_id
    assert login.json()["rol"] == "empresa"

    auditoria = client.get(
        "/api/v1/admin/auditoria", params={"accion": "empresa_activada"}
    )
    assert auditoria.status_code == 200, auditoria.text
    assert any(
        "Reactivación de prueba" in (e["detalle"] or "")
        for e in auditoria.json()["items"]
    )


def test_admin_listado_empresas_filtra_por_sector_activo_y_busqueda(client):
    id_1 = _registrar(client, NOMBRE_1, "RUC-ADM-FILTRO-1", "tecnologia")
    _registrar(client, NOMBRE_2, "RUC-ADM-FILTRO-2", "turismo")

    por_sector = client.get(
        "/api/v1/admin/empresas", params={"sector": "tecnologia"}
    )
    assert por_sector.status_code == 200, por_sector.text
    assert por_sector.json()["total"] == 1
    assert por_sector.json()["items"][0]["nombre_empresa"] == NOMBRE_1

    empresa_id = client.get(
        "/api/v1/admin/empresas", params={"busqueda": NOMBRE_1}
    ).json()["items"][0]["id"]
    suspendida = client.put(
        f"/api/v1/admin/empresas/{empresa_id}/estado", json={"activo": False}
    )
    assert suspendida.status_code == 200, suspendida.text

    inactivas = client.get(
        "/api/v1/admin/empresas", params={"activo": False}
    )
    assert inactivas.status_code == 200, inactivas.text
    assert inactivas.json()["total"] == 1
    assert inactivas.json()["items"][0]["cuenta_activa"] is False

    activas = client.get("/api/v1/admin/empresas", params={"activo": True})
    assert activas.status_code == 200, activas.text
    assert activas.json()["total"] == 1

    por_ruc = client.get(
        "/api/v1/admin/empresas", params={"busqueda": "RUC-ADM-FILTRO-1"}
    )
    assert por_ruc.status_code == 200, por_ruc.text
    assert por_ruc.json()["total"] == 1
    assert por_ruc.json()["items"][0]["id"] == empresa_id
    assert id_1  # La cuenta creada corresponde a la empresa filtrada.
