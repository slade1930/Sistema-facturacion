import inspect
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.ml.asistente import catalogo, intenciones
from app.models.facturacion import EstadoFactura


def _linea(descripcion, cantidad, monto, producto_id=None):
    return SimpleNamespace(
        descripcion=descripcion,
        producto_id=producto_id,
        cantidad=Decimal(str(cantidad)),
        monto=Decimal(str(monto)),
    )


def _factura(fid, fecha, total, estado, cliente, lineas=None, en_revision=False):
    return SimpleNamespace(
        id=fid,
        numero_serie=f"FAC-{fid:04d}",
        fecha=fecha,
        total=Decimal(str(total)),
        estado=estado,
        en_revision=en_revision,
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
        (_linea("Agua", 2, "20.00", 1), _linea("Jugo", 1, "30.00", 2)),
    ),
    _factura(
        2,
        date(2026, 10, 20),
        "500.00",
        EstadoFactura.ANULADA,
        "Acme",
        (_linea("Agua", 9, "90.00", 1),),
    ),
    _factura(
        3,
        date(2026, 11, 2),
        "200.00",
        EstadoFactura.EMITIDA,
        "Beta",
        (_linea("Agua", 5, "50.00", 1),),
        en_revision=True,
    ),
    _factura(
        4,
        date(2026, 11, 10),
        "300.00",
        EstadoFactura.EMITIDA,
        "Beta",
        (_linea("Jugo", 10, "100.00", 2), _linea("Agua", 1, "10.00", 1)),
    ),
)


@pytest.fixture
def repositorio(monkeypatch):
    vistos = []

    def listar(
        db,
        *,
        estado=None,
        en_revision=None,
        fecha_desde=None,
        fecha_hasta=None,
        cliente=None,
        skip=0,
        limit=50,
    ):
        vistos.append(
            {
                "estado": estado,
                "en_revision": en_revision,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "cliente": cliente,
                "skip": skip,
                "limit": limit,
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
        if en_revision is not None:
            resultados = [
                f
                for f in resultados
                if bool(getattr(f, "en_revision", False)) == en_revision
            ]
        if fecha_desde:
            resultados = [f for f in resultados if f.fecha >= fecha_desde]
        if fecha_hasta:
            resultados = [f for f in resultados if f.fecha <= fecha_hasta]
        if cliente:
            resultados = [
                f for f in resultados if cliente.lower() in f.cliente_nombre.lower()
            ]
        return resultados[skip : skip + limit]

    class Clientes:
        def __init__(self, db):
            pass

        def get(self, cliente_id):
            if cliente_id == 3:
                return SimpleNamespace(nombre_empresa="Acme")
            return None

    monkeypatch.setattr(catalogo.FacturaRepository, "listar", staticmethod(listar))
    monkeypatch.setattr(catalogo, "ClienteB2BRepository", Clientes)
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
    assert resultado["truncado"] is False
    assert repositorio[0]["fecha_desde"] == date(2026, 10, 1)
    assert repositorio[0]["fecha_hasta"] == date(2026, 10, 31)
    assert repositorio[0]["limit"] == catalogo.PAGINA


def test_ventas_por_cliente_agrupa(repositorio):
    resultado = catalogo.ventas_por_cliente(None, anio=2026)
    totales = {fila["cliente"]: fila["total"] for fila in resultado["datos"]}
    assert totales == {"Acme": "100.00", "Beta": "500.00"}


def test_ventas_por_producto_agrupa_lineas(repositorio):
    resultado = catalogo.ventas_por_producto(None, anio=2026)
    productos = {fila["producto"]: fila["total"] for fila in resultado["datos"]}
    assert productos == {"Agua": "80.00", "Jugo": "130.00"}
    assert {fila["producto_id"] for fila in resultado["datos"]} == {1, 2}
    assert "sin ITBMS ni portes" in resultado["nota"]


def test_facturas_anuladas_usa_estado_y_revision_usa_la_columna(repositorio):
    anuladas = catalogo.facturas_anuladas(None)
    revision = catalogo.facturas_en_revision(None)
    assert anuladas["cantidad"] == 1
    assert anuladas["datos"][0]["numero_serie"] == "FAC-0002"
    assert revision["cantidad"] == 1
    assert revision["datos"][0]["numero_serie"] == "FAC-0003"
    assert repositorio[0]["estado"] == EstadoFactura.ANULADA
    assert repositorio[1]["estado"] is None
    assert repositorio[1]["en_revision"] is True
    assert anuladas["truncado"] is False
    assert revision["truncado"] is False


def test_top_productos_ordena_por_unidades(repositorio):
    resultado = catalogo.top_productos(None, n=2)
    assert [fila["producto"] for fila in resultado["datos"]] == ["Jugo", "Agua"]
    assert resultado["filtros"]["n"] == 2
    assert resultado["detalle"].startswith("top 2")


def test_top_cero_devuelve_vacio(repositorio):
    resultado = catalogo.top_productos(None, n=0)
    assert resultado["datos"] == []
    assert resultado["filtros"]["n"] == 0


def test_cliente_id_se_resuelve_a_nombre(repositorio):
    resultado = catalogo.ventas_por_cliente(None, cliente_id=3)
    assert resultado["total"] == "100.00"
    assert repositorio[0]["cliente"] == "Acme"
    assert resultado["filtros"]["cliente_id"] == 3


def test_cliente_inexistente_devuelve_vacio(repositorio):
    resultado = catalogo.ventas_por_cliente(None, cliente_id=99)
    assert resultado["datos"] == []
    assert resultado["total"] == "0.00"
    assert "no existe" in resultado["detalle"]
    assert repositorio == []


def test_filtro_por_nombre_es_exacto(monkeypatch):
    datos = (
        _factura(1, date(2026, 10, 5), "10.00", EstadoFactura.EMITIDA, "Acme"),
        _factura(2, date(2026, 10, 6), "20.00", EstadoFactura.EMITIDA, "Acme Sur"),
    )
    monkeypatch.setattr(
        catalogo.FacturaRepository, "listar", staticmethod(lambda db, **kw: list(datos))
    )
    resultado = catalogo.ventas_por_cliente(None, cliente="Acme")
    assert [fila["cliente"] for fila in resultado["datos"]] == ["Acme"]
    assert resultado["total"] == "10.00"


def test_normalizar_cliente_ignora_puntuacion_y_acentos():
    assert catalogo.normalizar_cliente("Acme S.A.") == "acme s a"
    assert catalogo.normalizar_cliente("  Cía. Beta  ") == "cia beta"


@pytest.mark.parametrize(
    "consulta, guardado, esperado",
    [
        ("acme", "Acme S.A.", True),
        ("acme s.a", "Acme S.A.", True),
        ("beta", "Beta SRL", True),
        ("acme", "Acme Sur", False),
        ("acme sur", "Acme S.A.", False),
        ("acme s.a", "Acme", False),
        ("", "Acme", False),
    ],
)
def test_clientes_coinciden(consulta, guardado, esperado):
    assert catalogo.clientes_coinciden(consulta, guardado) is esperado


def test_razon_social_compuesta_no_queda_vacia(monkeypatch):
    datos = (
        _factura(1, date(2026, 10, 5), "10.00", EstadoFactura.EMITIDA, "Acme S.A."),
        _factura(2, date(2026, 10, 6), "20.00", EstadoFactura.EMITIDA, "Acme Sur"),
    )
    monkeypatch.setattr(
        catalogo.FacturaRepository, "listar", staticmethod(lambda db, **kw: list(datos))
    )
    resultado = catalogo.ventas_por_cliente(None, cliente="acme")
    assert [fila["cliente"] for fila in resultado["datos"]] == ["Acme S.A."]
    assert resultado["total"] == "10.00"
    assert resultado["truncado"] is False

    resultado = catalogo.ventas_por_cliente(None, cliente="acme s.a")
    assert [fila["cliente"] for fila in resultado["datos"]] == ["Acme S.A."]
    assert resultado["total"] == "10.00"

    resultado = catalogo.ventas_por_cliente(None, cliente="acme sur")
    assert [fila["cliente"] for fila in resultado["datos"]] == ["Acme Sur"]
    assert resultado["total"] == "20.00"


def test_cliente_con_acento_no_se_pierde(monkeypatch):
    datos = (
        _factura(1, date(2026, 10, 5), "30.00", EstadoFactura.EMITIDA, "Compañía La Acme"),
        _factura(2, date(2026, 10, 6), "20.00", EstadoFactura.EMITIDA, "Acme Sur"),
    )
    vistos = []

    def listar(db, **kw):
        vistos.append(kw.get("cliente"))
        if kw.get("cliente"):
            busqueda = kw["cliente"].lower()
            return [f for f in datos if busqueda in f.cliente_nombre.lower()]
        return list(datos)

    monkeypatch.setattr(
        catalogo.FacturaRepository, "listar", staticmethod(listar)
    )
    resultado = catalogo.ventas_por_cliente(None, cliente="compania la acme")
    assert all(valor is None for valor in vistos)
    assert [fila["cliente"] for fila in resultado["datos"]] == ["Compañía La Acme"]
    assert resultado["total"] == "30.00"


def test_truncamiento_se_reporta(monkeypatch, repositorio):
    monkeypatch.setattr(catalogo, "LIMITE", 2)
    resultado = catalogo.ventas_por_mes(None)
    assert resultado["truncado"] is True
    assert repositorio[0]["limit"] == catalogo.PAGINA
    assert len(resultado["datos"]) <= 2


def test_truncamiento_cuenta_solo_facturables(monkeypatch):
    datos = (
        _factura(1, date(2026, 10, 1), "10.00", EstadoFactura.ANULADA, "Acme"),
        _factura(2, date(2026, 10, 2), "20.00", EstadoFactura.ANULADA, "Acme"),
        _factura(3, date(2026, 10, 3), "30.00", EstadoFactura.EMITIDA, "Acme"),
    )
    monkeypatch.setattr(
        catalogo.FacturaRepository, "listar", staticmethod(lambda db, **kw: list(datos))
    )
    monkeypatch.setattr(catalogo, "LIMITE", 1)
    resultado = catalogo.ventas_por_mes(None)
    assert resultado["total"] == "30.00"
    assert resultado["truncado"] is False


def test_producto_id_agrupa_descripciones_distintas(monkeypatch):
    datos = (
        _factura(
            1,
            date(2026, 10, 1),
            "100.00",
            EstadoFactura.EMITIDA,
            "Acme",
            (_linea("Agua", 1, "70.00", 1), _linea("Agua light", 1, "30.00", 1)),
        ),
    )
    monkeypatch.setattr(
        catalogo.FacturaRepository, "listar", staticmethod(lambda db, **kw: list(datos))
    )
    resultado = catalogo.ventas_por_producto(None)
    assert len(resultado["datos"]) == 1
    assert resultado["datos"][0]["producto_id"] == 1
    assert resultado["datos"][0]["producto"] == "Agua"
    assert resultado["datos"][0]["total"] == "100.00"


def test_dia_y_rango_se_envian_al_repositorio(repositorio):
    catalogo.ventas_por_mes(None, anio=2026, mes=10, dia=5)
    assert repositorio[0]["fecha_desde"] == date(2026, 10, 5)
    assert repositorio[0]["fecha_hasta"] == date(2026, 10, 5)
    catalogo.ventas_por_mes(None, desde="2026-01-01", hasta="2026-03-31")
    assert repositorio[1]["fecha_desde"] == date(2026, 1, 1)
    assert repositorio[1]["fecha_hasta"] == date(2026, 3, 31)


def test_mes_sin_anio_usa_hoy_inyectable(repositorio):
    catalogo.ventas_por_mes(None, mes=10, hoy=date(2026, 11, 26))
    assert repositorio[0]["fecha_desde"] == date(2026, 10, 1)
    assert repositorio[0]["fecha_hasta"] == date(2026, 10, 31)


def test_redondeo_es_half_up():
    assert catalogo._dinero(Decimal("1.005")) == "1.01"


def test_de_intencion_a_catalogo_mes_sin_anio(repositorio):
    clasificacion = intenciones.clasificar(
        "¿Cuánto facturamos en octubre?", hoy=date(2026, 11, 26)
    )
    resultado = intenciones.ejecutar(None, clasificacion)
    assert resultado["total"] == "100.00"
    assert repositorio[0]["fecha_desde"] == date(2026, 10, 1)
    assert repositorio[0]["fecha_hasta"] == date(2026, 10, 31)
