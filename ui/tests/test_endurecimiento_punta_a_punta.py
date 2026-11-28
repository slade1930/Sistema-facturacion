"""Punta a punta del portal con backend simulado y sesión inyectada.

Las pantallas de las etapas B y C no viven en esta rama; se usan las pantallas
dobles de ``soporte_endurecimiento``. Cada prueba comprueba únicamente lo que el
backend simulado devuelve y lo que la interfaz muestra a partir de eso.
"""

from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.testing import user_simulation

from soporte_endurecimiento import (
    PRODUCTOS,
    TOKEN_ADMIN,
    BackendSimulado,
    instalar_dobles,
    pagina_admin,
    pagina_carrito,
    pagina_catalogo,
    pagina_compra_exitosa,
    pagina_empresa_privada,
    pagina_factura_detalle,
    pagina_facturas,
    pagina_login,
    pagina_registro,
)
from state.cliente_api import ErrorApi


@pytest.fixture
def entorno(monkeypatch):
    return instalar_dobles(monkeypatch, BackendSimulado())


def _campo(user, etiqueta: str, valor: str) -> None:
    elemento = next(
        elemento
        for elemento in user.find(ui.input).elements
        if elemento.props.get("label") == etiqueta
    )
    with user.client:
        elemento.value = valor


def _selector(user, etiqueta: str, valor: str) -> None:
    elemento = next(
        elemento
        for elemento in user.find(ui.select).elements
        if elemento.props.get("label") == etiqueta
    )
    with user.client:
        elemento.value = valor


@pytest.mark.anyio
async def test_endurecimiento_registro_login_catalogo_compra_factura_pdf(entorno):
    backend, auth, destinos = entorno.backend, entorno.auth, entorno.destinos

    async with user_simulation(root=pagina_registro(backend, auth)) as user:
        await user.open("/")
        for etiqueta, valor in (
            ("Nombre de la empresa", "Empresa Uno"),
            ("RUC", "123456789-1"),
            ("Correo electrónico", "uno@ejemplo.local"),
            ("Dirección", "Avenida Central"),
            ("Teléfono", "60000000"),
            ("Sucursal", "Central"),
            ("Contraseña", "<controlado>"),
        ):
            _campo(user, etiqueta, valor)
        _selector(user, "Sector", "tecnologia")
        user.find(kind=ui.button, content="Crear empresa").click()
        await user.should_see("Empresa creada. Bienvenida a tu portal.")

    token = auth.token()
    assert destinos[-1] == "/portal/inicio"
    assert backend.empresa_por_nombre("empresa uno")["sector"] == "tecnologia"

    auth.cerrar_sesion()
    async with user_simulation(root=pagina_login(backend, auth)) as user:
        await user.open("/")
        _campo(user, "Empresa", "Empresa Uno")
        _campo(user, "Contraseña", "<controlado>")
        user.find(kind=ui.button, content="Entrar").click()
        await user.should_see("Sesión iniciada.")

    assert auth.token() == token

    async with user_simulation(root=pagina_catalogo(backend, auth)) as user:
        await user.open("/")
        await user.should_see("Servidor Orquídea")
        await user.should_not_see("Paquete turístico")
        user.find(kind=ui.button, content="Añadir Servidor Orquídea").click()

    assert len(backend.carrito(token)) == 1

    async with user_simulation(root=pagina_carrito(backend, auth)) as user:
        await user.open("/")
        await user.should_see("Servidor Orquídea")
        user.find(kind=ui.button, content="Confirmar compra").click()
        await user.should_see("Compra confirmada. Tu factura ya está lista.")

    factura = backend.facturas[0]
    assert factura["cliente_id"] == backend.empresa_por_nombre("empresa uno")["id"]
    assert destinos[-1].endswith(f"factura_id={factura['id']}")

    async with user_simulation(root=pagina_facturas(backend, auth)) as user:
        await user.open("/")
        await user.should_see("Mis facturas")
        await user.should_see(factura["numero_serie"])

    async with user_simulation(
        root=pagina_compra_exitosa(backend, auth, factura["id"])
    ) as user:
        await user.open("/")
        await user.should_see("Tu compra quedó registrada")
        await user.should_see(factura["numero_serie"])
        await user.should_see("Ver factura")

    async with user_simulation(
        root=pagina_factura_detalle(backend, auth, factura["id"])
    ) as user:
        await user.open("/")
        await user.should_see(factura["numero_serie"])
        user.find(kind=ui.button, content="Descargar PDF").click()
        await user.should_see("PDF disponible")

    assert any(
        ruta.endswith(f"/api/v1/facturas/{factura['id']}/pdf")
        for _, ruta in backend.llamadas
    )


@pytest.mark.anyio
async def test_endurecimiento_segunda_empresa_no_ve_datos_de_la_primera(entorno):
    backend, auth = entorno.backend, entorno.auth
    primera = backend.registrar(
        {"nombre_empresa": "Empresa Uno", "ruc": "1", "sector": "tecnologia"}
    )
    segunda = backend.registrar(
        {"nombre_empresa": "Empresa Dos", "ruc": "2", "sector": "turismo"}
    )
    backend.anadir(primera["token"], PRODUCTOS[0])
    compra = backend.comprar(
        primera["token"], backend.carrito(primera["token"]), "idempotencia-controlada"
    )
    auth.guardar_sesion(segunda)

    async with user_simulation(root=pagina_catalogo(backend, auth)) as user:
        await user.open("/")
        await user.should_see("Paquete turístico")
        await user.should_not_see("Servidor Orquídea")

    async with user_simulation(root=pagina_facturas(backend, auth)) as user:
        await user.open("/")
        await user.should_see("Mis facturas")
        await user.should_not_see(compra["numero_serie"])

    assert backend.historial(segunda["token"]) == []
    assert backend.pedidos_de(segunda["token"]) == []
    assert backend.carrito(segunda["token"]) == []
    with pytest.raises(ErrorApi) as informacion:
        backend.factura(segunda["token"], compra["factura_id"])
    assert informacion.value.status_code == 404


@pytest.mark.anyio
async def test_endurecimiento_admin_ve_ambas_empresas_y_panel_suma(entorno):
    backend, auth = entorno.backend, entorno.auth
    for nombre, sector, producto in (
        ("Empresa Uno", "tecnologia", PRODUCTOS[0]),
        ("Empresa Dos", "turismo", PRODUCTOS[1]),
    ):
        respuesta = backend.registrar(
            {"nombre_empresa": nombre, "ruc": nombre, "sector": sector}
        )
        backend.anadir(respuesta["token"], producto)
        backend.comprar(
            respuesta["token"], backend.carrito(respuesta["token"]), "idempotencia-controlada"
        )

    auth.guardar_sesion(
        {
            "token": TOKEN_ADMIN,
            "rol": "admin",
            "cuenta_id": 0,
            "empresa": {"id": 0, "nombre": "Administración"},
        }
    )
    async with user_simulation(root=pagina_admin(backend, auth, "/admin/panel")) as user:
        await user.open("/")
        await user.should_see("Panel del administrador: /admin/panel")
        await user.should_see("Empresa Uno")
        await user.should_see("Empresa Dos")
        await user.should_see("Empresas: 2")
        await user.should_see("Total facturado: 600.00")

    assert backend.admin_resumen(TOKEN_ADMIN) == {
        "empresas": 2,
        "pedidos": 2,
        "facturas": 2,
        "facturado": "600.00",
    }
    assert len(backend.admin_empresas(TOKEN_ADMIN)) == 2


@pytest.mark.anyio
async def test_endurecimiento_empresa_suspendida_no_entra(entorno):
    backend, auth, destinos = entorno.backend, entorno.auth, entorno.destinos
    respuesta = backend.registrar(
        {"nombre_empresa": "Empresa Uno", "ruc": "1", "sector": "tecnologia"}
    )
    backend.suspender("Empresa Uno")
    auth.guardar_sesion(respuesta)
    auth.cerrar_sesion()

    async with user_simulation(root=pagina_login(backend, auth)) as user:
        await user.open("/")
        _campo(user, "Empresa", "Empresa Uno")
        _campo(user, "Contraseña", "<controlado>")
        user.find(kind=ui.button, content="Entrar").click()
        await user.should_see("Esta empresa está suspendida.")

    assert auth.token() is None
    assert destinos == []


@pytest.mark.anyio
async def test_endurecimiento_sesion_expirada_vuelve_al_login(entorno):
    backend, auth, destinos = entorno.backend, entorno.auth, entorno.destinos
    respuesta = backend.registrar(
        {"nombre_empresa": "Empresa Uno", "ruc": "1", "sector": "tecnologia"}
    )
    auth.guardar_sesion(respuesta)
    backend.expirar(respuesta["token"])

    async with user_simulation(root=pagina_facturas(backend, auth)) as user:
        await user.open("/")
        await user.should_see("Inicia sesión para entrar al portal.")
        await user.should_see("Ir a iniciar sesión")

    assert destinos == ["/login"]
    with pytest.raises(ErrorApi) as informacion:
        backend.historial(respuesta["token"])
    assert informacion.value.status_code == 401


@pytest.mark.anyio
async def test_endurecimiento_redirecciones_por_rol(entorno):
    backend, auth, destinos = entorno.backend, entorno.auth, entorno.destinos
    respuesta = backend.registrar(
        {"nombre_empresa": "Empresa Uno", "ruc": "1", "sector": "tecnologia"}
    )
    auth.guardar_sesion(respuesta)

    async with user_simulation(root=pagina_admin(backend, auth, "/admin")) as user:
        await user.open("/")
        await user.should_see("Inicia sesión para entrar al portal.")
        await user.should_see("Ir a iniciar sesión")

    assert destinos == ["/login"]

    auth.cerrar_sesion()
    async with user_simulation(root=pagina_empresa_privada(auth)) as user:
        await user.open("/")
        await user.should_see("Inicia sesión para entrar al portal.")
        await user.should_see("Ir a iniciar sesión")

    assert destinos == ["/login", "/login"]


@pytest.mark.anyio
async def test_endurecimiento_stock_insuficiente_sin_crear_nada(entorno):
    backend, auth = entorno.backend, entorno.auth
    respuesta = backend.registrar(
        {"nombre_empresa": "Empresa Uno", "ruc": "1", "sector": "tecnologia"}
    )
    auth.guardar_sesion(respuesta)
    backend.anadir(respuesta["token"], PRODUCTOS[3])
    antes = (
        len(backend.pedidos_registrados),
        len(backend.facturas),
        len(backend.movimientos),
        backend.stock[PRODUCTOS[3]["id"]],
    )

    async with user_simulation(root=pagina_carrito(backend, auth)) as user:
        await user.open("/")
        user.find(kind=ui.button, content="Confirmar compra").click()
        await user.should_see("Stock insuficiente para Artículo sin existencias.")

    assert (
        len(backend.pedidos_registrados),
        len(backend.facturas),
        len(backend.movimientos),
        backend.stock[PRODUCTOS[3]["id"]],
    ) == antes
    assert backend.historial(respuesta["token"]) == []
