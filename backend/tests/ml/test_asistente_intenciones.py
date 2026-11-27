import pytest

from app.ml.asistente import catalogo, intenciones


@pytest.mark.parametrize(
    "pregunta, nombre, parametros",
    [
        ("¿Cuánto facturamos en octubre?", "ventas_por_mes", {"mes": 10}),
        ("¿Cuánto facturamos en 2026-10?", "ventas_por_mes", {"anio": 2026, "mes": 10}),
        ("Ventas del cliente 3", "ventas_por_cliente", {"cliente": "3"}),
        ("Ventas por producto", "ventas_por_producto", {}),
        ("Facturas anuladas", "facturas_anuladas", {}),
        ("Productos más vendidos", "top_productos", {}),
        ("Facturas en revisión", "facturas_en_revision", {}),
        ("Top 3 productos", "top_productos", {"n": 3}),
    ],
)
def test_clasificar_preguntas_predefinidas(pregunta, nombre, parametros):
    resultado = intenciones.clasificar(pregunta)
    assert resultado is not None
    assert resultado.nombre == nombre
    for clave, valor in parametros.items():
        assert resultado.parametros.get(clave) == valor


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
    clasificacion = intenciones.clasificar("¿cuánto facturamos en noviembre?")
    assert intenciones.ejecutar(None, clasificacion) == {"ok": True}
    assert vistos == {"mes": 11}


def test_ejecutar_sin_intencion_no_llama_al_catalogo():
    assert intenciones.ejecutar(None, None) is None
