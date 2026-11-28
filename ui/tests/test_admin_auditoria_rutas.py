import sys
from pathlib import Path

import pytest
from nicegui.testing.user_simulation import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.admin import auditoria
from pages.facturacion import configuracion, nueva
from pages.pedidos import convertir_a_factura, pedidos_pendientes


@pytest.mark.anyio
async def test_admin_auditoria_muestra_eventos_y_paginacion(monkeypatch):
    monkeypatch.setattr(
        auditoria,
        "listar_auditoria",
        lambda api, filtros: {
            "items": [
                {
                    "id": 1,
                    "fecha": "2026-11-27T10:00:00",
                    "accion": "inicio_sesion",
                    "cuenta_id": 3,
                    "detalle": "Acceso correcto",
                    "ip": "127.0.0.1",
                }
            ],
            "total": 1,
            "desplazamiento": 0,
        },
    )

    async with user_simulation(root=auditoria.pagina_auditoria_admin) as user:
        await user.open("/")
        await user.should_see("Auditoría")
        await user.should_see("Acceso correcto")
        await user.should_see("Mostrando 1-1 de 1")


@pytest.mark.anyio
async def test_admin_auditoria_estado_vacio(monkeypatch):
    monkeypatch.setattr(
        auditoria,
        "listar_auditoria",
        lambda api, filtros: {"items": [], "total": 0, "desplazamiento": 0},
    )

    async with user_simulation(root=auditoria.pagina_auditoria_admin) as user:
        await user.open("/")
        await user.should_see("No hay eventos con estos filtros.")
        await user.should_see("Sin resultados")


@pytest.mark.anyio
async def test_admin_guardian_rige_las_rutas_compartidas(monkeypatch):
    casos = (
        (nueva, nueva.pagina_nueva, "Nueva factura"),
        (configuracion, configuracion.pagina_configuracion, "Configuración del negocio"),
        (
            pedidos_pendientes,
            pedidos_pendientes.pagina_pedidos_pendientes,
            "Pedidos por facturar",
        ),
        (
            convertir_a_factura,
            lambda: convertir_a_factura.pagina_convertir(pedido_id=12),
            "Facturar pedido #12",
        ),
    )

    for modulo, pagina, titulo in casos:
        monkeypatch.setattr(modulo, "exigir_admin", lambda: False)
        async with user_simulation(root=pagina) as user:
            await user.open("/")
            await user.should_not_see(titulo)
