from datetime import date

import pytest

from app.ml.asistente import catalogo, intenciones

HOY = date(2026, 11, 26)


@pytest.mark.parametrize(
    "pregunta, nombre, parametros",
    [
        ("¿Cuánto facturamos en octubre?", "ventas_por_mes", {"anio": 2026, "mes": 10}),
        ("¿Cuánto facturamos en 2026-10?", "ventas_por_mes", {"anio": 2026, "mes": 10}),
        ("Ventas del cliente 3", "ventas_por_cliente", {"cliente_id": 3}),
        ("Ventas por producto", "ventas_por_producto", {}),
        ("Facturas anuladas", "facturas_anuladas", {}),
        ("Productos más vendidos", "top_productos", {}),
        ("Facturas en revisión", "facturas_en_revision", {}),
        ("Top 3 productos", "top_productos", {"n": 3}),
    ],
)
def test_clasificar_preguntas_predefinidas(pregunta, nombre, parametros):
    resultado = intenciones.clasificar(pregunta, hoy=HOY)
    assert resultado is not None
    assert resultado.nombre == nombre
    for clave, valor in parametros.items():
        assert resultado.parametros.get(clave) == valor


@pytest.mark.parametrize(
    "pregunta, parametros",
    [
        ("Ventas por cliente Acme", {"cliente": "acme"}),
        ("Ventas por cliente Acme S.A.", {"cliente": "acme s.a"}),
        ("Ventas por cliente Acme S.A. en 2026", {"anio": 2026, "cliente": "acme s.a"}),
        ("Ventas por cliente Acme Sur en 2026", {"anio": 2026, "cliente": "acme sur"}),
        ("Ventas por cliente en 2026", {"anio": 2026}),
    ],
)
def test_cliente_por_nombre_compuesto(pregunta, parametros):
    resultado = intenciones.clasificar(pregunta, hoy=HOY)
    assert resultado is not None
    assert resultado.nombre == "ventas_por_cliente"
    assert resultado.parametros == parametros


@pytest.mark.parametrize(
    "pregunta, parametros",
    [
        ("Ventas de este año", {"anio": 2026}),
        ("Ventas del año pasado", {"anio": 2025}),
        ("Ventas de este mes", {"anio": 2026, "mes": 11}),
        ("Ventas de hoy", {"anio": 2026, "mes": 11, "dia": 26}),
        ("Ventas de ayer", {"anio": 2026, "mes": 11, "dia": 25}),
        (
            "Ventas entre enero y marzo de 2026",
            {"desde": "2026-01-01", "hasta": "2026-03-31"},
        ),
        ("Ventas del 2026-10-05", {"anio": 2026, "mes": 10, "dia": 5}),
    ],
)
def test_clasificar_fechas_relativas_y_rangos(pregunta, parametros):
    resultado = intenciones.clasificar(pregunta, hoy=HOY)
    assert resultado is not None
    assert resultado.parametros == parametros


@pytest.mark.parametrize(
    "pregunta",
    [
        "Ventas del 2026-02-31",
        "Ventas del 2026-13-05",
        "Ventas de 2026-13",
        "Ventas entre marzo y enero de 2026",
    ],
)
def test_fechas_invalidas_o_invertidas_no_clasifican(pregunta):
    assert intenciones.clasificar(pregunta, hoy=HOY) is None


def test_clasificar_sin_intencion_devuelve_none():
    assert intenciones.clasificar("hola, ¿cómo estás?") is None
    assert intenciones.clasificar("   ") is None


def test_clasificar_es_una_linea_base_sin_modelo():
    resultado = intenciones.clasificar("FACTURAS EN REVISIÓN")
    assert resultado.confianza >= intenciones.UMBRAL_CONFIANZA
    assert resultado.nombre in catalogo.CATALOGO


def test_ejecutar_despacha_al_catalogo(monkeypatch):
    vistos = {}

    def falso(db, **parametros):
        vistos.update(parametros)
        return {"ok": True}

    monkeypatch.setitem(intenciones.CATALOGO, "ventas_por_mes", falso)
    clasificacion = intenciones.clasificar(
        "¿cuánto facturamos en noviembre?", hoy=HOY
    )
    assert intenciones.ejecutar(None, clasificacion) == {"ok": True}
    assert vistos == {"mes": 11, "anio": 2026}


def test_ejecutar_sin_intencion_no_llama_al_catalogo():
    assert intenciones.ejecutar(None, None) is None
