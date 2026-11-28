import sys
from pathlib import Path
from typing import Any

import pytest
from nicegui.testing.user_simulation import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.admin import catalogo, empresas


class ApiEscritura:
    def __init__(self) -> None:
        self.llamadas: list[tuple[str, str, Any]] = []

    def post(self, ruta: str, json: Any = None) -> dict[str, Any]:
        self.llamadas.append(("POST", ruta, json))
        return {"id": 1}

    def put(self, ruta: str, json: Any = None) -> dict[str, Any]:
        self.llamadas.append(("PUT", ruta, json))
        return {"id": 1}


@pytest.mark.anyio
async def test_admin_empresas_muestra_tabla_y_formato(monkeypatch):
    monkeypatch.setattr(
        empresas,
        "listar_empresas",
        lambda api, filtros: {
            "items": [
                {
                    "id": 1,
                    "nombre_empresa": "Empresa de prueba",
                    "ruc": "123456789-0-1",
                    "sector": "tecnologia",
                    "activo": True,
                    "total_comprado": "125.5",
                    "fecha_ultima_compra": "2026-11-27",
                }
            ],
            "total": 1,
            "desplazamiento": 0,
        },
    )

    async with user_simulation(root=empresas.pagina_empresas_admin) as user:
        await user.open("/")
        await user.should_see("Empresas")
        await user.should_see("Empresa de prueba")
        await user.should_see("Tecnología")
        await user.should_see("Activa")
        await user.should_see("125.50")
        await user.should_see("Mostrando 1-1 de 1")


@pytest.mark.anyio
async def test_admin_empresas_estado_vacio(monkeypatch):
    monkeypatch.setattr(
        empresas,
        "listar_empresas",
        lambda api, filtros: {"items": [], "total": 0, "desplazamiento": 0},
    )

    async with user_simulation(root=empresas.pagina_empresas_admin) as user:
        await user.open("/")
        await user.should_see("No hay empresas con estos filtros.")
        await user.should_see("Sin resultados")


def test_admin_empresas_cambiar_estado_envia_solo_lo_del_backend():
    api = ApiEscritura()
    respuesta = empresas.cambiar_estado(api, 3, False, "Motivo de prueba")

    assert respuesta == {"id": 1}
    assert api.llamadas == [
        (
            "PUT",
            "/api/v1/admin/empresas/3/estado",
            {"activo": False, "motivo": "Motivo de prueba"},
        )
    ]


@pytest.mark.anyio
async def test_admin_catalogo_muestra_productos_y_precios(monkeypatch):
    monkeypatch.setattr(
        catalogo,
        "listar_categorias",
        lambda api, filtros: {
            "items": [
                {"id": 2, "nombre": "Bebidas", "sector": "supermercado", "total_productos": 1}
            ]
        },
    )
    monkeypatch.setattr(
        catalogo,
        "listar_productos",
        lambda api, filtros: {
            "items": [
                {
                    "id": 1,
                    "nombre": "Producto de prueba",
                    "sku": "PR-001",
                    "categoria_nombre": "Bebidas",
                    "sector": "supermercado",
                    "precio_caja": "12.5",
                    "precio_unidad": "1.25",
                    "existencias": 4,
                    "stock_minimo": 2,
                    "estado_activo": True,
                }
            ]
        },
    )

    async with user_simulation(root=catalogo.pagina_catalogo_admin) as user:
        await user.open("/")
        await user.should_see("Productos del catálogo")
        await user.should_see("Producto de prueba")
        await user.should_see("PR-001")
        await user.should_see("12.50")
        await user.should_see("1.25")
        await user.should_see("Activo")


@pytest.mark.anyio
async def test_admin_catalogo_estado_vacio(monkeypatch):
    monkeypatch.setattr(
        catalogo,
        "listar_categorias",
        lambda api, filtros: {"items": []},
    )
    monkeypatch.setattr(
        catalogo,
        "listar_productos",
        lambda api, filtros: {"items": []},
    )

    async with user_simulation(root=catalogo.pagina_catalogo_admin) as user:
        await user.open("/")
        await user.should_see("No hay productos con estos filtros.")


@pytest.mark.anyio
async def test_admin_categorias_muestra_listado(monkeypatch):
    monkeypatch.setattr(
        catalogo,
        "listar_categorias",
        lambda api, filtros: {
            "items": [
                {"id": 2, "nombre": "Bebidas", "sector": "supermercado", "total_productos": 3}
            ]
        },
    )

    async with user_simulation(root=catalogo.pagina_categorias_admin) as user:
        await user.open("/")
        await user.should_see("Categorías del catálogo")
        await user.should_see("Bebidas")
        await user.should_see("Supermercado")
        await user.should_see("3")


def test_admin_catalogo_filtra_stock_sobre_campos_del_backend():
    productos = [
        {"id": 1, "existencias": 0, "stock_minimo": 2},
        {"id": 2, "existencias": 1, "stock_minimo": 2},
        {"id": 3, "existencias": 5, "stock_minimo": 2},
    ]

    assert [item["id"] for item in catalogo.filtrar_stock(productos, "con")] == [2, 3]
    assert [item["id"] for item in catalogo.filtrar_stock(productos, "sin")] == [1]
    assert [item["id"] for item in catalogo.filtrar_stock(productos, "bajo")] == [1, 2]
    assert [item["id"] for item in catalogo.filtrar_stock(productos, "")] == [1, 2, 3]


def test_admin_catalogo_guarda_producto_segun_el_identificador():
    api = ApiEscritura()
    datos = {"nombre": "Producto de prueba"}

    catalogo.guardar_producto(api, None, datos)
    catalogo.guardar_producto(api, 4, datos)
    catalogo.guardar_categoria(api, None, {"nombre": "Bebidas"})
    catalogo.guardar_categoria(api, 2, {"nombre": "Bebidas"})

    assert [llamada[:2] for llamada in api.llamadas] == [
        ("POST", "/api/v1/admin/catalogo/productos"),
        ("PUT", "/api/v1/admin/catalogo/productos/4"),
        ("POST", "/api/v1/admin/catalogo/categorias"),
        ("PUT", "/api/v1/admin/catalogo/categorias/2"),
    ]
