from datetime import date

import pytest

from app.ml.evaluacion.asistente import evaluar_asistente
from app.ml.modelos import asistente as modelo

HOY = date(2026, 11, 26)
NOMBRE_PRUEBA = "asistente_evaluacion.pt"


@pytest.fixture(scope="module")
def modelo_entrenado(tmp_path_factory):
    pytest.importorskip("torch")
    carpeta = tmp_path_factory.mktemp("evaluacion")
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(modelo, "CARPETA_MODELOS", carpeta)
        from app.ml.entrenamiento import entrenar_asistente

        datos = entrenar_asistente.entrenar_asistente(guardar=False, epocas=400)
        if datos is None:
            pytest.skip("sin torch")
        ruta = modelo.guardar(datos, NOMBRE_PRUEBA)
        parche.setattr(modelo, "cargar_modelo", lambda nombre: ruta)
        yield ruta


def test_sin_modelo_solo_devuelve_linea_base(monkeypatch):
    monkeypatch.setattr(modelo, "disponible", lambda: False)

    resultado = evaluar_asistente(hoy=HOY)

    assert resultado["evaluado"] is False
    assert resultado["modelo"] is None
    assert resultado["linea_base"] == {
        "aciertos": 10,
        "total": 12,
        "precision": 0.8333,
    }
    assert resultado["red_local"] is None
    assert len(resultado["detalle"]) == 12
    assert all(fila["modelo"] is None for fila in resultado["detalle"])
    assert all(fila["confianza"] is None for fila in resultado["detalle"])


def test_sin_archivo_de_modelo_no_evalua(monkeypatch):
    monkeypatch.setattr(modelo, "disponible", lambda: True)
    monkeypatch.setattr(modelo, "cargar_modelo", lambda nombre: None)

    def no_predecir(*args, **kwargs):
        raise AssertionError("no se debe predecir sin archivo")

    monkeypatch.setattr(modelo, "predecir", no_predecir)

    resultado = evaluar_asistente(hoy=HOY)

    assert resultado["evaluado"] is False
    assert resultado["red_local"] is None


def test_modelo_entrenado_mejora_la_linea_base(modelo_entrenado):
    resultado = evaluar_asistente(hoy=HOY)

    assert resultado["evaluado"] is True
    assert resultado["modelo"] == modelo.NOMBRE_PUBLICO
    assert resultado["linea_base"] == {
        "aciertos": 10,
        "total": 12,
        "precision": 0.8333,
    }
    assert resultado["red_local"] == {
        "aciertos": 12,
        "total": 12,
        "precision": 1.0,
    }


def test_detalle_incluye_parametros_y_confianza(modelo_entrenado):
    detalle = evaluar_asistente(hoy=HOY)["detalle"]
    by_frase = {fila["frase"]: fila for fila in detalle}

    fila = by_frase["Ventas del cliente 4"]
    assert fila["esperado"] == "ventas_por_cliente"
    assert fila["linea_base"] == "ventas_por_cliente"
    assert fila["modelo"] == "ventas_por_cliente"
    assert fila["parametros_linea_base"] == {"cliente_id": 4}
    assert fila["parametros_modelo"] == {"cliente_id": 4}
    assert modelo.UMBRAL_CONFIANZA <= fila["confianza"] <= 1.0

    fila = by_frase["Top 2 productos del mes"]
    assert fila["parametros_modelo"] == {"n": 2}
    assert fila["confianza"] > 0


def test_frases_vacias_devuelve_metricas_en_cero(monkeypatch):
    monkeypatch.setattr(modelo, "disponible", lambda: False)

    resultado = evaluar_asistente(frases=[], hoy=HOY)

    assert resultado["evaluado"] is False
    assert resultado["linea_base"] == {
        "aciertos": 0,
        "total": 0,
        "precision": 0.0,
    }
    assert resultado["red_local"] is None
    assert resultado["detalle"] == []


def test_hoy_se_propaga_a_los_parametros(monkeypatch):
    monkeypatch.setattr(modelo, "disponible", lambda: False)
    frases = [("Facturas en revisión de hoy", "facturas_en_revision")]

    resultado = evaluar_asistente(frases=frases, hoy=date(2026, 12, 1))

    assert resultado["detalle"][0]["parametros_linea_base"] == {
        "anio": 2026,
        "mes": 12,
        "dia": 1,
    }
