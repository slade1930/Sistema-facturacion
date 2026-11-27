import inspect
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.ml.asistente import catalogo
from app.models.facturacion import EstadoFactura


def _linea(descripcion, cantidad, monto):
    return SimpleNamespace(
        descripcion=descripcion,
        cantidad=Decimal(str(cantidad)),
        monto=Decimal(str(monto)),
    )


def _factura(fid, fecha, total, estado, cliente, lineas=None):
    return SimpleNamespace(
        id=fid,
        numero_serie=f"FAC-{fid:04d}",
        fecha=fecha,
        total=Decimal(str(total)),
        estado=estado,
        cliente_nombre=cliente,
        lineas=lineas or (),
    )


FACTURAS = (
    _factura(
        1,
        date(2026, 10, 5),
        "100.00",
        EstadoFactura.EMITIDA,
        "Acme",
        (_linea("Agua", 2, "20.00"), _linea("Jugo", 1, "30.00")),
    ),
    _factura(
        2,
        date(2026, 10, 20),
        "500.00",
        EstadoFactura.ANULADA,
        "Acme",
        (_linea("Agua", 9, "90.00"),),
    ),
    _factura(
        3,
        date(2026, 11, 2),
        "200.00",
        EstadoFactura.EN_REVISION,
        "Beta",
        (_linea("Agua", 5, "50.00"),),
    ),
    _factura(
        4,
        date(2026, 11, 10),
        "300.00",
        EstadoFactura.EMITIDA,
        "Beta",
        (_linea("Jugo", 10, "100.00"), _linea("Agua", 1, "10.00")),
    ),
)


@pytest.fixture
def repositorio(monkeypatch):
    vistos = []

    def listar(
        db,
        *,
        estado=None,
        fecha_desde=None,
        fecha_hasta=None,
        cliente=None,
        skip=0,
        limit=50,
    ):
        vistos.append(
            {
                "estado": estado,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "cliente": cliente,
            }
        )
        resultados = list(FACTURAS)
        if estado is not None:
            valor = estado.value if hasattr(estado, "value") else str(estado)
            resultados = [
                f
                for f in resultados
                if (f.estado.value if hasattr(f.estado, "value") else str(f.estado))
                == valor
            ]
        if fecha_desde:
            resultados = [f for f in resultados if f.fecha >= fecha_desde]
        if fecha_hasta:
            resultados = [f for f in resultados if f.fecha <= fecha_hasta]
        if cliente:
            resultados = [f for f in resultados if cliente.lower() in f.cliente_nombre.lower()]
        return resultados

    monkeypatch.setattr(catalogo.FacturaRepository, "listar", staticmethod(listar))
    return vistos


def test_catalogo_no_construye_sql():
    fuente = inspect.getsource(catalogo)
    assert "select(" not in fuente
    assert "text(" not in fuente
    assert set(catalogo.CATALOGO) == set(catalogo.INTENCIONES)


def test_ventas_por_mes_excluye_anuladas_y_filtra(repositorio):
    resultado = catalogo.ventas_por_mes(None, anio=2026, mes=10)
    assert resultado["datos"] == [
        {"mes": "2026-10", "total": "100.00", "facturas": 1}
    ]
    assert resultado["total"] == "100.00"
    assert repositorio[0]["fecha_desde"] == date(2026, 10, 1)
    assert repositorio[0]["fecha_hasta"] == date(2026, 10, 31)


def test_ventas_por_cliente_agrupa(repositorio):
    resultado = catalogo.ventas_por_cliente(None, anio=2026)
    totales = {fila["cliente"]: fila["total"] for fila in resultado["datos"]}
    assert totales == {"Acme": "100.00", "Beta": "500.00"}


def test_ventas_por_producto_agrupa_lineas(repositorio):
    resultado = catalogo.ventas_por_producto(None, anio=2026)
    productos = {fila["producto"]: fila["total"] for fila in resultado["datos"]}
    assert productos == {"Agua": "80.00", "Jugo": "130.00"}


def test_facturas_anuladas_y_en_revision_usan_el_estado(repositorio):
    anuladas = catalogo.facturas_anuladas(None)
    revision = catalogo.facturas_en_revision(None)
    assert anuladas["cantidad"] == 1
    assert anuladas["datos"][0]["numero_serie"] == "FAC-0002"
    assert revision["cantidad"] == 1
    assert revision["datos"][0]["numero_serie"] == "FAC-0003"
    assert repositorio[0]["estado"] == EstadoFactura.ANULADA
    assert repositorio[1]["estado"] == EstadoFactura.EN_REVISION


def test_top_productos_ordena_por_unidades(repositorio):
    resultado = catalogo.top_productos(None, n=2)
    assert [fila["producto"] for fila in resultado["datos"]] == ["Jugo", "Agua"]
    assert resultado["filtros"]["n"] == 2
    assert resultado["detalle"].startswith("top 2")
