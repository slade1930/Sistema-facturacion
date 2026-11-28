import sys
from pathlib import Path
from typing import Any

import pytest
from nicegui.testing.user_simulation import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.admin import panel


class ApiFalsa:
    def __init__(self, respuestas: dict[str, Any]) -> None:
        self.respuestas = respuestas
        self.llamadas: list[tuple[str, str, Any]] = []

    def get(self, ruta: str, params: dict[str, Any] | None = None) -> Any:
        self.llamadas.append(("GET", ruta, params))
        return self.respuestas[ruta]

    def post(self, ruta: str, json: Any = None) -> Any:
        self.llamadas.append(("POST", ruta, json))
        return self.respuestas.get(ruta)


def _respuestas(*, evaluado: bool = True, facturas: bool = True) -> dict[str, Any]:
    respuesta: dict[str, Any] = {
        "/api/v1/admin/panel/resumen": {
            "desde": "2026-11-01",
            "hasta": "2026-11-28",
            "empresas_total": 4,
            "empresas_activas": 3,
            "empresas_en_linea": 2,
            "pedidos_por_facturar": 5,
            "facturas_en_revision": 1,
            "productos_bajo_minimo": 2,
            "ingresos_periodo": "1234.5",
            "facturas_periodo": 9,
        },
        "/api/v1/admin/panel/ingresos": {
            "por_mes": [{"mes": "2026-11", "ingresos": "100.00"}],
            "por_empresa": [{"nombre": "Empresa de prueba", "ingresos": "60.00"}],
            "por_sector": [],
            "por_categoria": [],
        },
        "/api/v1/admin/panel/productos": {
            "mas_pedidos_por_unidades": [
                {
                    "producto_id": 1,
                    "nombre": "Producto de prueba",
                    "sku": "PR-001",
                    "unidades": 10,
                    "monto": "100.00",
                    "pedidos": 2,
                }
            ],
            "mas_pedidos_por_monto": [],
            "menos_pedidos": [],
        },
        "/api/v1/ml/pronostico": {
            "evaluado": evaluado,
            "modelo": "modelo-de-prueba",
            "resultado": {"periodos": ["2026-12"], "valores": [150.0]},
        },
        "/api/v1/historial": {
            "items": (
                [
                    {
                        "id": 7,
                        "numero_serie": "FAC-2026-0007",
                        "total": "10.50",
                    }
                ]
                if facturas
                else []
            )
        },
        "/api/v1/ml/anomalias/evaluar/7": {
            "evaluado": evaluado,
            "resultado": {
                "factura_id": 7,
                "puntaje_anomalia": 0.9,
                "en_revision": True,
                "motivo_anomalia": "Monto fuera de patron",
            },
        },
    }
    return respuesta


@pytest.mark.anyio
async def test_admin_panel_muestra_metricas_y_llama_al_ml(monkeypatch):
    api = ApiFalsa(_respuestas())
    monkeypatch.setattr(panel, "cliente_admin", lambda: api)

    async with user_simulation(root=panel.pagina_panel) as user:
        await user.open("/")
        await user.should_see("Panel de control")
        await user.should_see("Empresas activas")
        await user.should_see("1234.50")
        await user.should_see("Ingresos por mes")
        await user.should_see("Anomalías sugeridas por el modelo")
        await user.should_see("FAC-2026-0007")
        await user.should_see("Estado: En revisión")
        await user.should_see("Monto fuera de patron")

    rutas = [llamada[1] for llamada in api.llamadas]
    assert "/api/v1/ml/pronostico" in rutas
    assert "/api/v1/ml/anomalias/evaluar/7" in rutas
    assert "/api/v1/admin/panel/resumen" in rutas
    assert "/api/v1/admin/panel/ingresos" in rutas
    assert "/api/v1/admin/panel/productos" in rutas


@pytest.mark.anyio
async def test_admin_panel_sin_modelo_dice_sin_evaluar(monkeypatch):
    api = ApiFalsa(_respuestas(evaluado=False))
    monkeypatch.setattr(panel, "cliente_admin", lambda: api)

    async with user_simulation(root=panel.pagina_panel) as user:
        await user.open("/")
        await user.should_see("Proyección: sin evaluar")
        await user.should_see("Estado: sin evaluar")


@pytest.mark.anyio
async def test_admin_panel_sin_facturas_en_revision(monkeypatch):
    api = ApiFalsa(_respuestas(facturas=False))
    monkeypatch.setattr(panel, "cliente_admin", lambda: api)

    async with user_simulation(root=panel.pagina_panel) as user:
        await user.open("/")
        await user.should_see("No hay facturas en revisión.")

    assert not any(
        llamada[1].startswith("/api/v1/ml/anomalias/evaluar/")
        for llamada in api.llamadas
    )


def test_admin_panel_evaluar_anomalia_tolera_respuesta_vacia():
    class ApiVacia:
        def post(self, ruta: str) -> None:
            return None

    assert panel.evaluar_anomalia(ApiVacia(), 7) == {}
