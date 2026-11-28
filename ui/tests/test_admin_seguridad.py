import sys
from pathlib import Path

import pytest
from nicegui import ui
from nicegui.testing import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components import layout, portal, sesion
from components.admin import api as api_admin
from components.admin import menu, seguridad
from components.admin.formato import VACIO, dinero, fecha, numero, texto
from components.admin.constantes import rango_periodo
from pages.facturacion import configuracion, nueva
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


@pytest.mark.anyio
@pytest.mark.parametrize(
    "modulo, pagina, titulo, datos",
    [
        (nueva, nueva.pagina_nueva, "Nueva factura", None),
        (
            configuracion,
            configuracion.pagina_configuracion,
            "Configuración del negocio",
            {},
        ),
    ],
)
async def test_paginas_compartidas_esperan_la_sesion(
    monkeypatch, modulo, pagina, titulo, datos
):
    """Sin esperar la pestaña, el guardián veía un token ausente y volvía al login."""
    destinos: list[str] = []
    estado: dict[str, str | bool | None] = {"token": None, "conectado": False}
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))
    monkeypatch.setattr(auth, "token", lambda: estado["token"], raising=False)
    monkeypatch.setattr(
        auth, "datos_usuario", lambda: {"rol": "admin"}, raising=False
    )

    async def conectar() -> None:
        estado["conectado"] = True
        estado["token"] = "token-de-la-pestaña"

    monkeypatch.setattr(modulo, "conectar_sesion", conectar, raising=False)
    monkeypatch.setattr(modulo, "listar_clientes", lambda cliente: [], raising=False)
    monkeypatch.setattr(
        modulo, "obtener_configuracion", lambda cliente: datos or {}, raising=False
    )
    monkeypatch.setattr(
        modulo, "_recomendaciones_pendientes", lambda cliente: False, raising=False
    )

    async with user_simulation(root=pagina) as user:
        await user.open("/")
        await user.should_see(titulo)

    assert estado["conectado"] is True
    assert estado["token"] == "token-de-la-pestaña"
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


def test_admin_y_portal_usan_la_misma_cabecera():
    cabecera_admin = sesion.cabecera_html(
        sesion.SECCIONES_ADMIN,
        "/admin/panel",
        href="/admin/panel",
        etiqueta="Ir al panel",
        accion=sesion.ACCION_EMITIR,
        directas=sesion.DIRECTAS_ADMIN,
        prefijo="orq-admin",
    )
    cabecera_portal = sesion.cabecera_html(
        sesion.SECCIONES_PORTAL,
        "/portal/inicio",
        href="/portal/inicio",
        etiqueta="Ir al inicio",
        accion=sesion.ACCION_PEDIDO,
        prefijo="orq-portal",
    )

    for cabecera in (cabecera_admin, cabecera_portal):
        assert "orq-header-inner" in cabecera
        assert "orq-petala" in cabecera
        assert "Orquídea" in cabecera
        assert "orq-nav-escritorio" in cabecera
        assert "orq-header-acciones" in cabecera
        assert "orq-hamburguesa" in cabecera
        assert "orq-cajon" in cabecera

    assert "Administración" not in cabecera_admin
    assert "Portal de empresas" not in cabecera_portal


@pytest.mark.anyio
async def test_paginas_compartidas_muestran_la_cabecera_del_admin(monkeypatch):
    """Las rutas compartidas y el panel usan exactamente el mismo encabezado."""
    monkeypatch.setattr(auth, "token", lambda: "token-admin", raising=False)
    monkeypatch.setattr(
        auth, "datos_usuario", lambda: {"rol": "admin"}, raising=False
    )
    monkeypatch.setattr(layout, "nombre_negocio", lambda: "", raising=False)
    monkeypatch.setattr(menu, "nombre_negocio", lambda: "", raising=False)

    async def cabecera_de(root):
        async with user_simulation(root=root) as user:
            await user.open("/")
            elementos = [
                elemento
                for elemento in user.find(ui.html).elements
                if "orq-header-inner" in elemento.props.get("innerHTML", "")
            ]
            assert len(elementos) == 1
            return elementos[0]

    cabecera_panel = await cabecera_de(
        lambda: menu.montar_admin("Configuración", ruta_activa="/configuracion")
    )
    cabecera_compartida = await cabecera_de(
        lambda: layout.montar_layout(None, ruta_activa="/configuracion")
    )

    assert (
        cabecera_compartida.props["innerHTML"] == cabecera_panel.props["innerHTML"]
    )
    assert "orq-admin" in cabecera_compartida._classes
    assert "orq-admin-enlace" in cabecera_compartida.props["innerHTML"]


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
