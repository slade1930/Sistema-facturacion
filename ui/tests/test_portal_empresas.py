import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from nicegui import ui
from nicegui.testing import User, user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components.auth import cumple_politica
from pages.auth import cambiar_clave, login, registro
from pages.empresa import carrito as portal_carrito
from pages.empresa import compra_exitosa, facturas, inicio, mi_cuenta, pedidos
from state import auth
from state.cliente_api import ClienteApi, ErrorApi


class ApiFalsa:
    """Backend simulado: solo devuelve lo que la empresa podría recibir."""

    client = object()

    def __init__(self, respuestas: dict[str, Any] | None = None) -> None:
        self.respuestas = respuestas or {}
        self.llamadas: list[tuple[str, dict[str, Any]]] = []

    def get(self, ruta: str, **kwargs: Any) -> Any:
        self.llamadas.append((ruta, kwargs))
        for sufijo, valor in self.respuestas.items():
            if ruta.endswith(sufijo):
                return valor
        return {}

    def post(self, ruta: str, **kwargs: Any) -> Any:
        self.llamadas.append((ruta, kwargs))
        for sufijo, valor in self.respuestas.items():
            if ruta.endswith(sufijo):
                return valor
        return {}


def _establecer_input(user: User, etiqueta: str, valor: str) -> None:
    elemento = next(
        elemento
        for elemento in user.find(ui.input).elements
        if elemento.props.get("label") == etiqueta
    )
    with user.client:
        elemento.value = valor


@pytest.fixture
def sesion_portal(monkeypatch):
    almacen: dict[str, Any] = {}
    monkeypatch.setattr(auth, "_almacen", lambda: almacen)
    monkeypatch.setattr(auth, "token", lambda: "token-de-prueba")
    monkeypatch.setattr(
        auth,
        "datos_usuario",
        lambda: {
            "rol": "empresa",
            "cuenta_id": 3,
            "empresa": {"id": 7, "nombre": "Empresa Uno", "ruc": "123456789-1"},
        },
    )

    async def conectar() -> None:
        return None

    monkeypatch.setattr(auth, "conectar", conectar)
    return almacen


def test_token_viaja_en_privadas_y_no_en_publicas():
    vistos: dict[str, dict[str, str | None]] = {"privada": {}, "publica": {}}

    def manejador(solicitud):
        destino = "publica" if solicitud.url.path.startswith("/api/v1/verificar") else "privada"
        vistos[destino] = {
            "api_key": solicitud.headers.get("X-API-Key"),
            "authorization": solicitud.headers.get("Authorization"),
        }
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(manejador)
    with ClienteApi(
        base_url="http://backend:8000",
        api_key="clave-de-prueba",
        token="token-de-prueba",
        client=httpx.Client(transport=transport),
    ) as cliente:
        cliente.get("/api/v1/productos")
        cliente.get("/api/v1/verificar", params={"numero_serie": "FAC-1", "codigo": "abc"})

    assert vistos["privada"]["api_key"] == "clave-de-prueba"
    assert vistos["privada"]["authorization"] == "Bearer token-de-prueba"
    assert vistos["publica"] == {"api_key": None, "authorization": None}


def test_guardar_sesion_cambia_de_cuenta_y_cierra(monkeypatch):
    almacen: dict[str, Any] = {"carrito": [{"producto_id": 1}], auth.CLAVE_COMPRA: "abc"}
    monkeypatch.setattr(auth, "_almacen", lambda: almacen)

    auth.guardar_sesion(
        {
            "token": "token-nuevo",
            "rol": "empresa",
            "cuenta_id": 9,
            "empresa": {"id": 7, "nombre": "Empresa Dos"},
            "debe_cambiar_clave": False,
        }
    )

    assert auth.token() == "token-nuevo"
    assert auth.datos_usuario()["cuenta_id"] == 9
    assert auth.nombre_empresa() == "Empresa Dos"
    assert "carrito" not in almacen
    assert auth.CLAVE_COMPRA not in almacen

    auth.cerrar_sesion()
    assert almacen == {}


@pytest.mark.parametrize(
    "clave, esperado",
    [
        ("Abcdefg1", True),
        ("ABCDEFGH1", True),
        ("abcdefg1", False),
        ("Abcdef1", False),
        ("A" * 64 + "1", False),
    ],
)
def test_politica_de_contrasena(clave, esperado):
    assert cumple_politica(clave) is esperado


@pytest.mark.anyio
async def test_login_guarda_sesion_y_entra_al_portal(monkeypatch):
    almacen: dict[str, Any] = {}
    destinos: list[str] = []
    monkeypatch.setattr(auth, "_almacen", lambda: almacen)
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))
    monkeypatch.setattr(
        login,
        "enviar_login",
        lambda empresa, contrasena: {
            "token": "token-login",
            "rol": "empresa",
            "cuenta_id": 4,
            "empresa": {"id": 7, "nombre": "Empresa Uno", "ruc": "123"},
            "debe_cambiar_clave": False,
        },
    )

    async with user_simulation(root=login.pagina_login) as user:
        await user.open("/")
        _establecer_input(user, "Empresa", "Empresa Uno")
        _establecer_input(user, "Contraseña", "Clave123")
        user.find(kind=ui.button, content="Entrar").click()
        await user.should_see("Sesión iniciada.")

    assert almacen["portal_token"] == "token-login"
    assert destinos == ["/portal/inicio"]


@pytest.mark.anyio
async def test_login_muestra_error_sin_guardar_token(monkeypatch):
    almacen: dict[str, Any] = {}
    monkeypatch.setattr(auth, "_almacen", lambda: almacen)

    def rechazar(empresa, contrasena):
        raise ErrorApi(401, "Empresa o contraseña incorrectos", "UNAUTHORIZED")

    monkeypatch.setattr(login, "enviar_login", rechazar)

    async with user_simulation(root=login.pagina_login) as user:
        await user.open("/")
        _establecer_input(user, "Empresa", "Empresa Uno")
        _establecer_input(user, "Contraseña", "Clave123")
        user.find(kind=ui.button, content="Entrar").click()
        await user.should_see("Empresa o contraseña incorrectos")

    assert auth.token() is None


@pytest.mark.anyio
async def test_registro_guarda_sesion_y_entra_al_portal(monkeypatch):
    almacen: dict[str, Any] = {}
    destinos: list[str] = []
    vistos: dict[str, Any] = {}
    monkeypatch.setattr(auth, "_almacen", lambda: almacen)
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))

    def falso_registro(datos):
        vistos.update(datos)
        return {
            "token": "token-registro",
            "rol": "empresa",
            "cuenta_id": 5,
            "empresa": {"id": 7, "nombre": "Empresa Nueva", "ruc": "123"},
            "debe_cambiar_clave": False,
        }

    monkeypatch.setattr(registro, "enviar_registro", falso_registro)

    async with user_simulation(root=registro.pagina_registro) as user:
        await user.open("/")
        for etiqueta, valor in (
            ("Nombre de la empresa", "Empresa Nueva"),
            ("RUC", "123"),
            ("Correo electrónico", "nueva@ejemplo.local"),
            ("Dirección", "Calle 1"),
            ("Teléfono", "60000000"),
            ("Sucursal", "Central"),
            ("Contraseña", "Clave1234"),
        ):
            _establecer_input(user, etiqueta, valor)
        selector = next(
            elemento
            for elemento in user.find(ui.select).elements
            if elemento.props.get("label") == "Sector"
        )
        with user.client:
            selector.value = "tecnologia"
        user.find(kind=ui.button, content="Crear empresa").click()
        await user.should_see("Empresa creada. Bienvenida a tu portal.")

    assert vistos["nombre_empresa"] == "Empresa Nueva"
    assert vistos["sector"] == "tecnologia"
    assert vistos["contrasena"] == "Clave1234"
    assert almacen["portal_token"] == "token-registro"
    assert destinos == ["/portal/inicio"]


@pytest.mark.anyio
async def test_cambiar_clave_envia_la_nueva_y_vuelve_al_inicio(monkeypatch, sesion_portal):
    vistos: dict[str, str] = {}
    destinos: list[str] = []
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))

    def falso_cambio(actual, nueva):
        vistos["actual"] = actual
        vistos["nueva"] = nueva
        return {"detalle": "Contraseña actualizada."}

    monkeypatch.setattr(cambiar_clave, "enviar_cambio", falso_cambio)

    async with user_simulation(root=cambiar_clave.pagina_cambiar_clave) as user:
        await user.open("/")
        _establecer_input(user, "Contraseña actual", "Clave1234")
        _establecer_input(user, "Nueva contraseña", "Clave5678")
        user.find(kind=ui.button, content="Guardar contraseña").click()
        await user.should_see("Contraseña actualizada.")

    assert vistos == {"actual": "Clave1234", "nueva": "Clave5678"}
    assert destinos == ["/portal/inicio"]


@pytest.mark.anyio
async def test_panel_muestra_solo_lo_que_devuelve_el_backend(monkeypatch, sesion_portal):
    api = ApiFalsa(
        {
            "/historial": {
                "items": [
                    {
                        "id": 1,
                        "numero_serie": "FAC-2026-0009",
                        "fecha": "2026-11-27",
                        "cliente_nombre": "Empresa Uno",
                        "total": "10.00",
                        "estado": "emitida",
                    }
                ]
            },
            "/pedidos": {"items": [{"id": 5, "estado": "pendiente", "lineas": []}]},
            "/productos": [{"id": 2, "nombre": "Producto del sector"}],
            "/recomendaciones": {
                "resultado": {
                    "recomendaciones": [{"producto_id": 2, "puntaje": 0.8}]
                }
            },
        }
    )
    monkeypatch.setattr(auth, "cliente_portal", lambda: api)

    async with user_simulation(root=inicio.pagina_inicio) as user:
        await user.open("/")
        await user.should_see("Portal de empresas")
        await user.should_see("Total facturado")
        await user.should_see("FAC-2026-0009")
        await user.should_see("Recomendaciones para tu empresa")
        await user.should_not_see("Emitir factura")

    rutas = [ruta for ruta, _ in api.llamadas]
    assert any(ruta.endswith("/historial") for ruta in rutas)
    assert any(ruta.endswith("/pedidos") for ruta in rutas)
    assert any(ruta.endswith("/productos") for ruta in rutas)


@pytest.mark.anyio
async def test_portal_sin_token_pide_login(monkeypatch):
    monkeypatch.setattr(auth, "token", lambda: None)

    async def conectar() -> None:
        return None

    monkeypatch.setattr(auth, "conectar", conectar)

    async with user_simulation(root=facturas.pagina_facturas_empresa) as user:
        await user.open("/")
        await user.should_see("Inicia sesión para entrar al portal.")
        await user.should_see("Ir a iniciar sesión")


@pytest.mark.anyio
async def test_facturas_y_pedidos_usan_rutas_propias(monkeypatch, sesion_portal):
    api = ApiFalsa(
        {
            "/historial": {
                "items": [
                    {
                        "id": 8,
                        "numero_serie": "FAC-2026-0010",
                        "fecha": "2026-11-27",
                        "cliente_nombre": "Empresa Uno",
                        "total": "25.00",
                        "estado": "emitida",
                    }
                ]
            },
            "/pedidos": {
                "items": [
                    {
                        "id": 12,
                        "estado": "pendiente",
                        "total_estimado": "25.00",
                        "factura_generada_id": 8,
                    }
                ]
            },
        }
    )
    monkeypatch.setattr(auth, "cliente_portal", lambda: api)

    async with user_simulation(root=facturas.pagina_facturas_empresa) as user:
        await user.open("/")
        await user.should_see("Mis facturas")
        await user.should_see("FAC-2026-0010")

    async with user_simulation(root=pedidos.pagina_pedidos_empresa) as user:
        await user.open("/")
        await user.should_see("Mis pedidos")
        await user.should_see("#12")
        await user.should_see("#8")

    assert any(ruta == "/api/v1/historial" for ruta, _ in api.llamadas)
    assert any(ruta == "/api/v1/pedidos" for ruta, _ in api.llamadas)


@pytest.mark.anyio
async def test_compra_confirma_y_lleva_a_la_factura(monkeypatch, sesion_portal):
    carrito = [
        {
            "producto_id": 2,
            "nombre": "Producto del sector",
            "tipo_empaque": "caja",
            "cantidad": 2.0,
            "precio_caja": "10.00",
        }
    ]

    class SesionFalsa:
        def __init__(self) -> None:
            self.carrito = carrito

    destinos: list[str] = []
    vistos: dict[str, Any] = {}
    monkeypatch.setattr(portal_carrito, "sesion", SesionFalsa())
    monkeypatch.setattr(auth, "cliente_portal", lambda: ApiFalsa())
    monkeypatch.setattr(ui.navigate, "to", lambda destino: destinos.append(destino))
    monkeypatch.setattr(
        portal_carrito,
        "calcular",
        lambda api, datos: {
            "lineas": [
                {
                    "descripcion": "Producto del sector",
                    "tipo_empaque": "caja",
                    "cantidad": "2",
                    "precio_unitario": "10.00",
                    "subtotal": "20.00",
                }
            ],
            "subtotal": "20.00",
            "descuento_total": "0.00",
            "itbms": "0.00",
            "total": "20.00",
        },
    )

    def falso_comprar(api, lineas, clave):
        vistos["lineas"] = lineas
        vistos["clave"] = clave
        return {
            "pedido_id": 12,
            "factura_id": 8,
            "numero_serie": "FAC-2026-0010",
            "total": "20.00",
            "reutilizada": False,
        }

    monkeypatch.setattr(portal_carrito, "comprar", falso_comprar)

    async with user_simulation(root=portal_carrito.pagina_carrito_empresa) as user:
        await user.open("/")
        await user.should_see("Totales de tu compra")
        user.find(kind=ui.button, content="Confirmar compra").click()
        await user.should_see("Compra confirmada. Tu factura ya está lista.")

    assert vistos["lineas"][0]["producto_id"] == 2
    assert vistos["clave"]
    assert carrito == []
    assert destinos and destinos[0].startswith("/portal/compra-exitosa?")
    assert "factura_id=8" in destinos[0]


@pytest.mark.anyio
async def test_compra_exitosa_y_mi_cuenta(monkeypatch, sesion_portal):
    monkeypatch.setattr(
        mi_cuenta,
        "consultar",
        lambda api: {
            "rol": "empresa",
            "cuenta_id": 4,
            "debe_cambiar_clave": False,
            "empresa": {
                "nombre": "Empresa Uno",
                "ruc": "123",
                "sector": "tecnologia",
                "sucursal": "Centro",
            },
        },
    )

    async with user_simulation(
        root=lambda: compra_exitosa.pagina_compra_exitosa(
            factura_id=8,
            pedido_id=12,
            numero_serie="FAC-2026-0010",
            total="25.00",
        )
    ) as user:
        await user.open("/")
        await user.should_see("Tu compra quedó registrada")
        await user.should_see("FAC-2026-0010")
        await user.should_see("Ver factura")

    async with user_simulation(root=mi_cuenta.pagina_mi_cuenta) as user:
        await user.open("/")
        await user.should_see("Tecnología")
        await user.should_see("Cambiar contraseña")
