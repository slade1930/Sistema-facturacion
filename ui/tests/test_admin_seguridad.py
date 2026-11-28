import sys
from pathlib import Path

from nicegui import ui

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components import portal, sesion
from components.admin import api as api_admin
from components.admin import menu, seguridad
from components.admin.formato import VACIO, dinero, fecha, numero, texto
from components.admin.constantes import rango_periodo
from state import auth, cliente_api


MENU_ESPERADO = (
    ("Panel", (("Panel", "/admin/panel"),)),
    (
        "Facturación",
        (
            ("Emitir factura", "/facturacion/nueva"),
            ("Historial", "/facturacion/historial"),
        ),
    ),
    (
        "Catálogo",
        (
            ("Productos", "/admin/catalogo"),
            ("Categorías", "/admin/catalogo/categorias"),
        ),
    ),
    ("Inventario", (("Inventario", "/admin/inventario"),)),
    (
        "Pedidos",
        (
            ("Por facturar", "/admin/pedidos/por-facturar"),
            ("Todos", "/admin/pedidos"),
        ),
    ),
    ("Empresas", (("Empresas", "/admin/empresas"),)),
    (
        "Consultar",
        (
            ("Verificar factura", "/verificar"),
            ("Auditoría", "/admin/auditoria"),
        ),
    ),
    ("Negocio", (("Configuración", "/configuracion"),)),
)


def test_admin_guardian_acepta_la_sesion_stub(monkeypatch):
    monkeypatch.delattr(auth, "token", raising=False)
    monkeypatch.delattr(auth, "datos_usuario", raising=False)
    destinos = []
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))

    assert seguridad.exigir_admin() is True
    assert destinos == []


def test_admin_guardian_sin_token_va_al_ingreso(monkeypatch):
    monkeypatch.setattr(auth, "token", lambda: None, raising=False)
    monkeypatch.setattr(auth, "datos_usuario", lambda: {"rol": "admin"}, raising=False)
    destinos = []
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))

    assert seguridad.exigir_admin() is False
    assert destinos == ["/login"]


def test_admin_guardian_empresa_va_al_portal(monkeypatch):
    monkeypatch.setattr(auth, "token", lambda: object(), raising=False)
    monkeypatch.setattr(auth, "datos_usuario", lambda: {"rol": "empresa"}, raising=False)
    destinos = []
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))

    assert seguridad.exigir_admin() is False
    assert destinos == ["/portal/inicio"]


def test_admin_guardian_admin_puede_continuar(monkeypatch):
    monkeypatch.setattr(auth, "token", lambda: object(), raising=False)
    monkeypatch.setattr(auth, "datos_usuario", lambda: {"rol": "admin"}, raising=False)
    destinos = []
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))

    assert seguridad.exigir_admin() is True
    assert destinos == []


def test_admin_cliente_admin_usa_cliente_de_la_sesion(monkeypatch):
    class ClienteSesion:
        pass

    esperado = ClienteSesion()
    monkeypatch.setattr(auth, "cliente_portal", lambda: esperado, raising=False)

    assert api_admin.cliente_admin() is esperado


def test_admin_cliente_admin_cae_al_cliente_base(monkeypatch):
    class ClienteBase:
        pass

    monkeypatch.setattr(auth, "cliente_portal", None, raising=False)
    monkeypatch.setattr(cliente_api, "ClienteApi", ClienteBase)

    assert isinstance(api_admin.cliente_admin(), ClienteBase)


def test_admin_menu_es_el_acordado():
    assert menu.SECCIONES_ADMIN == MENU_ESPERADO
    assert menu.GRUPOS_ADMIN == frozenset(
        {"Facturación", "Catálogo", "Pedidos", "Consultar", "Negocio"}
    )
    assert menu.RUTAS_ADMIN >= {"/admin", "/admin/panel", "/admin/auditoria"}
    assert menu._activa("/admin") == "/admin/panel"
    assert menu._activa("/verificar") == "/verificar"


def test_admin_menu_publica_todos_los_enlaces():
    enlaces = {
        ruta for _, grupos in MENU_ESPERADO for _, ruta in grupos
    }
    escritorio = menu._navegacion("/admin/panel")
    movil = menu._enlaces_moviles("/admin/panel")

    for ruta in enlaces:
        assert f'href="{ruta}"' in escritorio
        assert f'href="{ruta}"' in movil
    assert 'aria-current="page"' in escritorio


def test_admin_y_portal_comparten_la_marca_pero_no_los_enlaces():
    marca_admin = sesion.marca("/admin/panel", "Ir al panel", "Administración")
    marca_portal = sesion.marca("/portal/inicio", "Ir al inicio", "Empresa Uno")

    for marca in (marca_admin, marca_portal):
        assert "orq-petala" in marca
        assert "Orquídea" in marca
        assert "orq-nombre-marca" in marca

    navegacion_admin = menu._navegacion("/admin/panel")
    navegacion_portal = portal._navegacion("/portal/inicio")

    assert "/admin/panel" in navegacion_admin
    assert "Auditoría" in navegacion_admin
    assert "/portal/" not in navegacion_admin

    assert "/portal/inicio" in navegacion_portal
    assert "/admin/" not in navegacion_portal
    assert "Auditoría" not in navegacion_portal
    assert "Panel" not in navegacion_portal


def test_admin_formato_muestra_lo_que_entrega_el_backend():
    assert dinero("10.5") == "10.50"
    assert dinero("10") == "10.00"
    assert dinero("1234.567") == "1234.567"
    assert dinero(None) == VACIO
    assert fecha("2026-11-27T10:30:00") == "2026-11-27"
    assert fecha(None) == VACIO
    assert numero("3.5") == 3.5
    assert numero("x") == 0.0
    assert texto(0) == "0"
    assert texto(None) == VACIO


def test_admin_rango_periodo_no_calcula_negocio():
    assert rango_periodo("todo") == (None, None)
    desde, hasta = rango_periodo("30")
    assert (hasta - desde).days == 30
    assert rango_periodo("anio")[0].month == 1
