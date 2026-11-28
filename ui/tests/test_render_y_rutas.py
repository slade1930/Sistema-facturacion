import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
from nicegui import core, ui
from nicegui.client import Client
from nicegui.testing import User
from nicegui.testing.user_simulation import user_simulation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pages.catalogo import catalogo
from pages.facturacion import configuracion, detalle, historial, nueva
from pages.pedidos import (
    convertir_a_factura,
    detalle_pedido,
    formulario_pedido,
    pedido_exitoso,
    pedidos_pendientes,
)
from pages.verificar import verificar
from state.cliente_api import ErrorApi


RUTAS_ESPERADAS = {
    "/",
    "/login",
    "/registro",
    "/portal/cambiar-clave",
    "/portal/carrito",
    "/portal/catalogo",
    "/portal/compra-exitosa",
    "/portal/factura-detalle",
    "/portal/facturas",
    "/portal/inicio",
    "/portal/mi-cuenta",
    "/portal/pedidos",
    "/catalogo",
    "/carrito",
    "/configuracion",
    "/facturacion/detalle",
    "/facturacion/historial",
    "/facturacion/nueva",
    "/pedidos/convertir-a-factura",
    "/pedidos/detalle",
    "/pedidos/formulario",
    "/pedidos/exitoso",
    "/pedidos/por-facturar",
    "/verificar",
}


def _cargar_app() -> object:
    """Carga `app.py` por ruta: evita confundirlo con el paquete `app` del contenedor."""
    nombre = "orquidea_app"
    # Cada simulación reinicia los registros globales de NiceGUI: volvemos a cargar
    # el módulo para que las rutas queden registradas también después de esas pruebas.
    sys.modules.pop(nombre, None)
    for modulo in list(sys.modules):
        if modulo == "pages" or modulo.startswith("pages."):
            sys.modules.pop(modulo, None)
    ruta = Path(__file__).resolve().parents[1] / "app.py"
    especificacion = importlib.util.spec_from_file_location(nombre, ruta)
    if especificacion is None or especificacion.loader is None:
        raise RuntimeError("No se pudo cargar la interfaz.")
    modulo = importlib.util.module_from_spec(especificacion)
    sys.modules[nombre] = modulo
    ejecutar = ui.run
    ui.run = lambda *args, **kwargs: None
    try:
        especificacion.loader.exec_module(modulo)
    finally:
        ui.run = ejecutar
    return modulo


def _establecer_input(user: User, etiqueta: str, valor: str) -> None:
    elemento = next(
        elemento
        for elemento in user.find(ui.input).elements
        if elemento.props.get("label") == etiqueta
    )
    with user.client:
        elemento.value = valor


def test_app_registra_todas_las_rutas(monkeypatch):
    monkeypatch.setattr(ui, "run", lambda *args, **kwargs: None)
    _cargar_app()

    rutas_registradas = {
        ruta
        for ruta in Client.page_routes.values()
    }

    assert rutas_registradas == RUTAS_ESPERADAS
    assert RUTAS_ESPERADAS <= {
        ruta.path for ruta in core.app.routes if hasattr(ruta, "path")
    }


@pytest.mark.anyio
async def test_inicio_renderiza_titulo_y_acciones():
    app = _cargar_app()

    async with user_simulation(root=app.inicio) as user:
        await user.open("/")
        await user.should_see("Tu facturación, en orden")
        await user.should_see("¿Qué quieres hacer?")
        await user.should_see("Verificación pública")


@pytest.mark.anyio
async def test_nueva_factura_renderiza_errors_de_validacion(monkeypatch):
    errores = [
        {"loc": ["body", "cliente_nombre"], "msg": "Field required"},
        {"loc": ["body", "lineas"], "msg": "List should have at least 1 item"},
    ]

    def rechazar_creacion(*args, **kwargs):
        raise ErrorApi(422, "Datos inválidos.", "VALIDATION_ERROR", errores)

    monkeypatch.setattr(nueva, "crear", rechazar_creacion)

    async with user_simulation(root=nueva.pagina_nueva) as user:
        await user.open("/")
        _establecer_input(user, "Cliente", "Cliente de prueba")
        _establecer_input(user, "Descripción", "Servicio")
        user.find(kind=ui.button, content="Emitir factura").click()

        await user.should_see("Datos inválidos.")
        await user.should_see("Cliente: falta este dato.")
        await user.should_see("Líneas: agrega al menos una línea.")


@pytest.mark.anyio
async def test_verificar_renderiza_errors_de_validacion(monkeypatch):
    errores = [
        {"loc": ["path", "numero_serie"], "msg": "Field required"},
        {"loc": ["path", "codigo"], "msg": "Field required"},
    ]

    def rechazar_consulta(*args, **kwargs):
        raise ErrorApi(422, "Datos inválidos.", "VALIDATION_ERROR", errores)

    monkeypatch.setattr(verificar, "consultar", rechazar_consulta)

    async with user_simulation(root=verificar.pagina_verificar) as user:
        await user.open("/")
        _establecer_input(user, "Número de serie", "FAC-2026-0001")
        _establecer_input(user, "Código de verificación", "abc123")
        user.find(kind=ui.button, content="Verificar").click()

        await user.should_see("Datos inválidos.")
        await user.should_see("Número de serie: falta este dato.")
        await user.should_see("Código de verificación: falta este dato.")


@pytest.mark.anyio
async def test_configuracion_renderiza_errors_de_validacion(monkeypatch):
    errores = [
        {"loc": ["body", "empresa_ruc"], "msg": "Field required"},
        {"loc": ["body", "empresa_nombre"], "msg": "Field required"},
    ]
    monkeypatch.setattr(
        configuracion,
        "obtener_configuracion",
        lambda cliente: {"empresa_nombre": "Empresa de prueba"},
    )

    def rechazar_actualizacion(*args, **kwargs):
        raise ErrorApi(422, "Datos inválidos.", "VALIDATION_ERROR", errores)

    monkeypatch.setattr(configuracion, "actualizar_configuracion", rechazar_actualizacion)

    async with user_simulation(root=configuracion.pagina_configuracion) as user:
        await user.open("/")
        user.find("Guardar").click()

        await user.should_see("Datos inválidos.")
        await user.should_see("RUC: falta este dato.")
        await user.should_see("Empresa: falta este dato.")


@pytest.mark.anyio
async def test_catalogo_renderiza_productos_y_precios(monkeypatch):
    monkeypatch.setattr(catalogo, "listar_categorias", lambda cliente: [])
    monkeypatch.setattr(
        catalogo,
        "listar_productos",
        lambda cliente, busqueda=None, categoria_id=None: [
            {
                "id": 1,
                "nombre": "Producto de prueba",
                "sku": "PR-001",
                "precio_caja": "12.50",
                "precio_unidad": "1.25",
            }
        ],
    )

    async with user_simulation(root=catalogo.pagina_catalogo) as user:
        await user.open("/")
        await user.should_see("Catálogo")
        await user.should_see("Producto de prueba")
        await user.should_see("SKU: PR-001")
        await user.should_see("Caja: 12.50")
        await user.should_see("Añadir al carrito")


@pytest.mark.anyio
async def test_historial_renderiza_facturas_y_resumen(monkeypatch):
    monkeypatch.setattr(
        historial,
        "consultar",
        lambda cliente, filtros: {
            "items": [
                {
                    "id": 1,
                    "numero_serie": "FAC-2026-0001",
                    "fecha": "2026-11-27",
                    "cliente_nombre": "Cliente de prueba",
                    "condicion_pago": "contado",
                    "total": "10.50",
                    "estado": "emitida",
                }
            ],
            "total": 1,
            "limite": 20,
            "desplazamiento": 0,
        },
    )

    async with user_simulation(root=historial.pagina_historial) as user:
        await user.open("/")
        await user.should_see("Facturas emitidas")
        await user.should_see("Cliente")
        await user.should_see("Buscar")
        await user.should_see("Mostrando 1-1 de 1")
        tabla = user.find(ui.table).elements.pop()
        assert tabla.rows[0]["numero_serie"] == "FAC-2026-0001"
        assert tabla.rows[0]["cliente_nombre"] == "Cliente de prueba"


@pytest.mark.anyio
async def test_detalle_factura_renderiza_datos_y_acciones(monkeypatch):
    monkeypatch.setattr(
        detalle,
        "obtener",
        lambda cliente, factura_id: {
            "id": factura_id,
            "numero_serie": "FAC-2026-0007",
            "estado": "emitida",
            "cliente_nombre": "Cliente de prueba",
            "total": "25.00",
            "lineas": [],
        },
    )

    async with user_simulation(root=lambda: detalle.pagina_detalle(factura_id=7)) as user:
        await user.open("/")
        await user.should_see("FAC-2026-0007")
        await user.should_see("Emitida")
        await user.should_see("Cliente de prueba")
        await user.should_see("25.00")
        await user.should_see("Anular")
        await user.should_see("Duplicar")
        await user.should_see("Descargar PDF")


@pytest.mark.anyio
async def test_pedidos_pendientes_renderiza_pedido_y_acciones(monkeypatch):
    monkeypatch.setattr(
        pedidos_pendientes,
        "listar_pendientes",
        lambda cliente, limite: [
            {
                "id": 12,
                "cliente_id": 3,
                "estado": "pendiente",
                "total_estimado": "30.00",
                "notas": "Entrega prioritaria",
                "lineas": [{"producto_id": 5}],
            }
        ],
    )

    async with user_simulation(root=pedidos_pendientes.pagina_pedidos_pendientes) as user:
        await user.open("/")
        await user.should_see("Pedidos por facturar")
        await user.should_see("Pedido #12 · pendiente")
        await user.should_see("Entrega prioritaria")
        await user.should_see("Ver detalle")
        await user.should_see("Facturar")


@pytest.mark.anyio
async def test_formulario_pedido_renderiza_clientes_y_carrito_vacio(monkeypatch):
    monkeypatch.setattr(formulario_pedido.sesion, "carrito", [])
    monkeypatch.setattr(
        formulario_pedido,
        "listar_clientes",
        lambda cliente: [{"id": 3, "nombre_empresa": "Cliente de prueba"}],
    )

    async with user_simulation(root=formulario_pedido.pagina_formulario_pedido) as user:
        await user.open("/")
        await user.should_see("Formulario de pedido")
        await user.should_see("Cliente")
        await user.should_see("El carrito está vacío.")
        await user.should_see("Crear pedido")


@pytest.mark.anyio
async def test_detalle_pedido_renderiza_lineas_y_accion(monkeypatch):
    monkeypatch.setattr(
        detalle_pedido,
        "obtener_pedido",
        lambda cliente, pedido_id: {
            "id": pedido_id,
            "cliente_id": 3,
            "estado": "pendiente",
            "total_estimado": "30.00",
            "lineas": [
                {
                    "orden": 1,
                    "producto_id": 5,
                    "tipo_empaque": "caja",
                    "cantidad": "2",
                    "subtotal": "30.00",
                }
            ],
        },
    )

    async with user_simulation(
        root=lambda: detalle_pedido.pagina_detalle_pedido(pedido_id=12)
    ) as user:
        await user.open("/")
        await user.should_see("Pedido #12")
        await user.should_see("pendiente")
        await user.should_see("Producto #5 · Caja")
        await user.should_see("30.00")
        await user.should_see("Convertir a factura")


@pytest.mark.anyio
async def test_pedido_exitoso_renderiza_resumen_y_enlaces(monkeypatch):
    monkeypatch.setattr(
        pedido_exitoso,
        "obtener_pedido",
        lambda cliente, pedido_id: {
            "id": pedido_id,
            "cliente_id": 3,
            "estado": "pendiente",
            "total_estimado": "30.00",
            "notas": "Entrega prioritaria",
            "fecha_creacion": "2026-11-27",
        },
    )

    async with user_simulation(
        root=lambda: pedido_exitoso.pagina_pedido_exitoso(pedido_id=12)
    ) as user:
        await user.open("/")
        await user.should_see("Pedido #12 creado")
        await user.should_see("Entrega prioritaria")
        await user.should_see("Ver pedidos por facturar")
        await user.should_see("Convertir a factura")


@pytest.mark.anyio
async def test_convertir_pedido_muestra_detail_code_y_errores_422(monkeypatch):
    errores = [
        {"loc": ["body", "pedido_id"], "msg": "Pedido inválido"},
        {"loc": ["body", "estado"], "msg": "Estado no permitido"},
    ]

    def rechazar_obtencion(*args, **kwargs):
        raise ErrorApi(422, "No se puede procesar el pedido.", "VALIDATION_ERROR", errores)

    monkeypatch.setattr(convertir_a_factura, "obtener_pedido", rechazar_obtencion)

    async with user_simulation(
        root=lambda: convertir_a_factura.pagina_convertir(pedido_id=12)
    ) as user:
        await user.open("/")
        await user.should_see("No se puede procesar el pedido.")
        await user.should_see("Pedido: Pedido inválido.")
        await user.should_see("Estado: Estado no permitido.")
