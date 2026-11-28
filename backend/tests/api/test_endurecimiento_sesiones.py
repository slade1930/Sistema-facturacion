"""Limpieza de sesiones vencidas con reloj controlado y cadencia horaria."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seguridad import Cuenta, RolCuenta, Sesion
from app.services import auth as servicio_auth

AHORA = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
REGISTRO = {
    "nombre_empresa": "Sesiones Endurecimiento",
    "ruc": "RUC-SESIONES-ENDURECIMIENTO",
    "direccion": "Avenida Central",
    "telefono": "60001111",
    "correo": "sesiones@ejemplo.local",
    "sucursal": "Central",
    "contrasena": "Clave1234",
    "sector": "tecnologia",
}


@pytest.fixture
def db(client) -> Session:
    from app.db.session import get_db
    from app.main import app

    generador = app.dependency_overrides[get_db]()
    sesion = next(generador)
    try:
        yield sesion
    finally:
        generador.close()


def _cuenta(db: Session, nombre: str = "admin-sesiones-endurecimiento") -> Cuenta:
    cuenta = Cuenta(
        nombre_usuario=nombre,
        password_hash="hash-de-prueba-sin-valor-real",
        rol=RolCuenta.ADMIN,
        activo=True,
    )
    db.add(cuenta)
    db.flush()
    return cuenta


def _sesion(
    db: Session,
    cuenta: Cuenta,
    etiqueta: str,
    *,
    creada_en: datetime,
    expira_en: datetime,
    revocada: bool = False,
) -> Sesion:
    sesion = Sesion(
        cuenta_id=cuenta.id,
        token_hash=servicio_auth.hash_token(f"token-prueba-{etiqueta}"),
        creada_en=creada_en,
        ultima_actividad=creada_en,
        expira_en=expira_en,
        revocada=revocada,
    )
    db.add(sesion)
    db.flush()
    return sesion


def _etiquetas(db: Session, cuenta_id: int) -> set[str]:
    hashes = set(
        db.scalars(
            select(Sesion.token_hash).where(Sesion.cuenta_id == cuenta_id)
        ).all()
    )
    return {
        nombre
        for nombre in (
            "vieja-expirada",
            "vieja-revocada",
            "vieja-vigente",
            "reciente-expirada",
            "nueva-expirada",
        )
        if servicio_auth.hash_token(f"token-prueba-{nombre}") in hashes
    }


def test_endurecimiento_limpia_sesiones_con_reloj_controlado(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(servicio_auth, "_ultima_limpieza_sesiones", None)
    cuenta = _cuenta(db)
    _sesion(
        db,
        cuenta,
        "vieja-expirada",
        creada_en=AHORA - timedelta(days=8),
        expira_en=AHORA - timedelta(hours=1),
    )
    _sesion(
        db,
        cuenta,
        "vieja-revocada",
        creada_en=AHORA - timedelta(days=8),
        expira_en=AHORA + timedelta(hours=1),
        revocada=True,
    )
    _sesion(
        db,
        cuenta,
        "vieja-vigente",
        creada_en=AHORA - timedelta(days=8),
        expira_en=AHORA + timedelta(hours=1),
    )
    _sesion(
        db,
        cuenta,
        "reciente-expirada",
        creada_en=AHORA - timedelta(days=2),
        expira_en=AHORA - timedelta(hours=1),
    )

    borradas = servicio_auth.limpiar_sesiones_vencidas(db, ahora=AHORA)

    assert borradas == 2
    db.expire_all()
    assert _etiquetas(db, cuenta.id) == {"vieja-vigente", "reciente-expirada"}


def test_endurecimiento_limpieza_sesiones_cadencia_horaria(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(servicio_auth, "_ultima_limpieza_sesiones", None)
    cuenta = _cuenta(db, "admin-cadencia-sesiones")

    servicio_auth.limpiar_sesiones_vencidas(db, ahora=AHORA)
    _sesion(
        db,
        cuenta,
        "nueva-expirada",
        creada_en=AHORA - timedelta(days=9),
        expira_en=AHORA - timedelta(hours=2),
    )

    omitidas = servicio_auth.limpiar_sesiones_vencidas(
        db, ahora=AHORA + timedelta(minutes=30)
    )
    db.expire_all()
    assert omitidas == 0
    assert "nueva-expirada" in _etiquetas(db, cuenta.id)

    borradas = servicio_auth.limpiar_sesiones_vencidas(
        db, ahora=AHORA + timedelta(hours=1, seconds=1)
    )
    db.expire_all()
    assert borradas == 1
    assert _etiquetas(db, cuenta.id) == set()


def test_endurecimiento_login_limpia_sesiones_como_maximo_una_vez_por_hora(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(servicio_auth, "_ultima_limpieza_sesiones", None)
    monkeypatch.setattr(servicio_auth, "ahora_utc", lambda: AHORA)
    registro = client.post("/api/v1/auth/registro", json=REGISTRO)
    assert registro.status_code == 200, registro.text
    cuenta = db.scalar(
        select(Cuenta).where(Cuenta.nombre_usuario == REGISTRO["nombre_empresa"].lower())
    )
    assert cuenta is not None

    _sesion(
        db,
        cuenta,
        "vieja-expirada",
        creada_en=AHORA - timedelta(days=8),
        expira_en=AHORA - timedelta(hours=1),
    )

    primer_login = client.post(
        "/api/v1/auth/login",
        json={
            "nombre_empresa": REGISTRO["nombre_empresa"],
            "contrasena": REGISTRO["contrasena"],
        },
    )
    assert primer_login.status_code == 200, primer_login.text
    db.expire_all()
    assert "vieja-expirada" not in _etiquetas(db, cuenta.id)

    _sesion(
        db,
        cuenta,
        "nueva-expirada",
        creada_en=AHORA - timedelta(days=9),
        expira_en=AHORA - timedelta(hours=1),
    )
    segundo_login = client.post(
        "/api/v1/auth/login",
        json={
            "nombre_empresa": REGISTRO["nombre_empresa"],
            "contrasena": REGISTRO["contrasena"],
        },
    )
    assert segundo_login.status_code == 200, segundo_login.text
    db.expire_all()
    assert "nueva-expirada" in _etiquetas(db, cuenta.id)
