import sys
from pathlib import Path

import pytest
from nicegui.testing.user_simulation import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.admin import inventario, pedidos, por_facturar


@pytest.mark.anyio
async def test_admin_inventario_muestra_alertas_y_movimientos(monkeypatch):
    monkeypatch.setattr(
        inventario,
        "listar_inventario",
        lambda api, parametros: [
            {
                "producto_id": 5,
                "nombre_producto": "Producto de prueba",
                "sku": "PR-001",
                "existencias": "2",
                "stock_minimo": "5",
                "actualizado_en": "2026-11-27T10:00:00",
            }
        ],
    )
    monkeypatch.setattr(
        inventario,
        "listar_movimientos",
        lambda api, filtros: {
            "items": [
                {
                    "id": 1,
                    "producto_id": 5,
                    "fecha": "2026-11-27",
                    "tipo": "entrada",
                    "cantidad": "3",
                    "motivo": "Reposicion",
                }
            ],
            "total": 1,
        },
    )

    async with user_simulation(root=inventario.pagina_inventario_admin) as user:
        await user.open("/")
        await user.should_see("Inventario")
        await user.should_see("Alertas bajo el mínimo")
        await user.should_see("Producto de prueba · 2 / 5")
        await user.should_see("Movimientos")
        await user.should_see("Entrada")
        await user.should_see("Reposicion")


@pytest.mark.anyio
async def test_admin_inventario_estados_vacios(monkeypatch):
    monkeypatch.setattr(inventario, "listar_inventario", lambda api, parametros: [])
    monkeypatch.setattr(
        inventario,
        "listar_movimientos",
        lambda api, filtros: {"items": [], "total": 0},
    )

    async with user_simulation(root=inventario.pagina_inventario_admin) as user:
        await user.open("/")
        await user.should_see("Ningún producto está bajo el mínimo.")
        await user.should_see("Todavía no hay existencias registradas.")
        await user.should_see("No hay movimientos con estos filtros.")


def test_admin_inventario_detecta_bajo_minimo():
    items = [
        {"producto_id": 1, "existencias": 1, "stock_minimo": 2},
        {"producto_id": 2, "existencias": 2, "stock_minimo": 2},
        {"producto_id": 3, "existencias": 4, "stock_minimo": 2},
    ]

    assert [item["producto_id"] for item in inventario.bajo_minimo(items)] == [1]


@pytest.mark.anyio
async def test_admin_pedidos_muestra_listado_y_paginacion(monkeypatch):
    monkeypatch.setattr(
        pedidos,
        "listar_pedidos",
        lambda api, filtros: {
            "items": [
                {
                    "id": 12,
                    "nombre_empresa": "Empresa de prueba",
                    "estado": "pendiente",
                    "total_estimado": "30.5",
                    "fecha_creacion": "2026-11-27",
                    "factura_generada_id": None,
                }
            ],
            "total": 1,
            "desplazamiento": 0,
        },
    )

    async with user_simulation(root=pedidos.pagina_pedidos_admin) as user:
        await user.open("/")
        await user.should_see("Todos los pedidos")
        await user.should_see("Empresa de prueba")
        await user.should_see("Pendiente")
        await user.should_see("30.50")
        await user.should_see("Mostrando 1-1 de 1")


@pytest.mark.anyio
async def test_admin_pedidos_estado_vacio(monkeypatch):
    monkeypatch.setattr(
        pedidos,
        "listar_pedidos",
        lambda api, filtros: {"items": [], "total": 0, "desplazamiento": 0},
    )

    async with user_simulation(root=pedidos.pagina_pedidos_admin) as user:
        await user.open("/")
        await user.should_see("No hay pedidos con estos filtros.")
        await user.should_see("Sin resultados")


@pytest.mark.anyio
async def test_admin_por_facturar_muestra_enlace_de_conversion(monkeypatch):
    monkeypatch.setattr(
        por_facturar,
        "listar_por_facturar",
        lambda api, limite: [
            {
                "id": 12,
                "nombre_empresa": "Empresa de prueba",
                "estado": "pendiente",
                "total_estimado": "30.5",
                "fecha_creacion": "2026-11-27",
                "notas": "Entrega prioritaria",
                "lineas": [
                    {
                        "producto_id": 5,
                        "tipo_empaque": "caja",
                        "cantidad": "2",
                        "subtotal": "30.50",
                    }
                ],
            }
        ],
    )

    async with user_simulation(root=por_facturar.pagina_por_facturar_admin) as user:
        await user.open("/")
        await user.should_see("Pedidos por facturar")
        await user.should_see("Entrega prioritaria")
        await user.should_see("Facturar pedido #12")


@pytest.mark.anyio
async def test_admin_por_facturar_estado_vacio(monkeypatch):
    monkeypatch.setattr(por_facturar, "listar_por_facturar", lambda api, limite: [])

    async with user_simulation(root=por_facturar.pagina_por_facturar_admin) as user:
        await user.open("/")
        await user.should_see("No hay pedidos pendientes de factura.")
