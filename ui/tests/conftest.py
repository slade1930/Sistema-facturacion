"""Sesión de administrador por defecto en las pruebas de la interfaz.

Las pantallas compartidas de facturación y pedidos pasan a ser solo de admin
en la etapa C. Las pruebas que no están enfocadas en la sesión necesitan una
sesión de administrador para poder renderizarlas. Las pruebas de seguridad
sobrescriben estos valores con ``monkeypatch`` dentro de cada caso, así que
las redirecciones de anónimo y de empresa siguen comprobándose de verdad.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state import auth


@pytest.fixture(autouse=True)
def sesion_admin_en_pruebas(monkeypatch, request):
    """Solo se activa cuando la etapa B aporta el módulo de sesión real."""
    # Las pruebas que comprueban la sesión en sí necesitan arrancar sin ella.
    if request.node.fspath.basename == "test_portal_empresas.py":
        return
    if not hasattr(auth, "token") or not hasattr(auth, "datos_usuario"):
        return
    monkeypatch.setattr(auth, "token", lambda: "sesion-admin-de-prueba")
    monkeypatch.setattr(
        auth,
        "datos_usuario",
        lambda: {"rol": "admin", "cuenta_id": 1, "empresa": {}},
    )
